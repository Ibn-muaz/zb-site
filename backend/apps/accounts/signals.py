"""
Accounts app Django signals - Lands and Houses

Signals:
  - post_save on CustomUser: sends a verification email when a new user is created.
  - user_logged_in: logs login activity via UserActivity.
  - user_logged_out: logs logout activity via UserActivity.
"""
import logging
import uuid

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request):
    """Safely extract the client IP from a request object (may be None)."""
    if request is None:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', None)


def _send_verification_email(user):
    """
    Send an account-verification email to the newly registered user.
    Uses HTML template when available; falls back to plain text.
    In development the console email backend prints to stdout.
    """
    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
        verify_url = f"{frontend_url}/accounts/verify-email/{user.verification_token}/"

        context = {
            'user': user,
            'verify_url': verify_url,
            'site_name': 'Lands and Houses',
        }

        try:
            html_message = render_to_string(
                'accounts/emails/verification_email.html', context
            )
            plain_message = strip_tags(html_message)
        except Exception:
            # Template not yet created – use a sensible plain-text fallback
            plain_message = (
                f"Hi {user.first_name},\n\n"
                f"Welcome to Lands and Houses!\n\n"
                f"Please verify your email address by visiting:\n"
                f"{verify_url}\n\n"
                f"This link expires after 24 hours.\n\n"
                f"If you did not register, please ignore this email.\n\n"
                f"Best regards,\nLands and Houses Team"
            )
            html_message = None

        send_mail(
            subject='Please Verify Your Email – Lands and Houses',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,      # Don't break registration if email fails
        )
        logger.info('Verification email dispatched to %s', user.email)

    except Exception as exc:
        logger.error(
            'signal: verification email failed for %s – %s', user.email, exc
        )


# ---------------------------------------------------------------------------
# post_save → CustomUser (new user creation)
# ---------------------------------------------------------------------------

@receiver(post_save, sender='accounts.CustomUser')
def handle_new_user(sender, instance, created, **kwargs):
    """
    Fires after a CustomUser is saved.

    On creation:
      - Ensure a verification token exists (may already be set by serializer).
      - Send a verification email (console backend in dev mode).
    """
    if not created:
        return

    # If the serializer already set a token, don't overwrite it
    if not instance.verification_token:
        token = str(uuid.uuid4()).replace('-', '')
        # Use update() to avoid triggering this signal again
        sender.objects.filter(pk=instance.pk).update(verification_token=token)
        instance.verification_token = token

    _send_verification_email(instance)


# ---------------------------------------------------------------------------
# user_logged_in signal
# ---------------------------------------------------------------------------

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Log every successful login to the UserActivity table.
    Imports are deferred to avoid AppRegistryNotReady at startup.
    """
    try:
        from apps.accounts.models import UserActivity  # deferred import

        ip = _get_client_ip(request)
        user_agent = (
            request.META.get('HTTP_USER_AGENT', '')[:200]
            if request else ''
        )

        UserActivity.objects.create(
            user=user,
            action='login',
            description=f'Login from {ip} | Agent: {user_agent}',
            ip_address=ip,
        )

        logger.info('User %s logged in from %s', user.email, ip)

    except Exception as exc:
        logger.warning('log_user_login signal error: %s', exc)


# ---------------------------------------------------------------------------
# user_logged_out signal
# ---------------------------------------------------------------------------

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Log every logout event to the UserActivity table.
    The `user` argument may be None if the session was already invalid.
    """
    if user is None:
        return

    try:
        from apps.accounts.models import UserActivity  # deferred import

        ip = _get_client_ip(request)

        UserActivity.objects.create(
            user=user,
            action='logout',
            description=f'Logout from {ip}',
            ip_address=ip,
        )

        logger.info('User %s logged out from %s', user.email, ip)

    except Exception as exc:
        logger.warning('log_user_logout signal error: %s', exc)
