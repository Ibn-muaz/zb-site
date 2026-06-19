"""
Accounts app serializers - Lands and Houses
Handles user registration, authentication, profile, and password management.
"""
import uuid
import logging
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed

from .models import CustomUser, UserActivity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UserMiniSerializer  (lightweight, for nested / read-only contexts)
# ---------------------------------------------------------------------------

class UserMiniSerializer(serializers.ModelSerializer):
    """Compact serializer for embedding user info in other serializers."""

    full_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'full_name', 'email', 'avatar']
        read_only_fields = ['id', 'full_name', 'email', 'avatar']

    def get_full_name(self, obj):
        return obj.full_name

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None


# ---------------------------------------------------------------------------
# UserRegisterSerializer
# ---------------------------------------------------------------------------

class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    - Validates passwords match and meet Django's validators.
    - Creates user with a hashed password.
    - Generates a verification token and sends a verification email.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label='Confirm Password',
        style={'input_type': 'password'},
    )

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'email',
            'password',
            'password2',
            'first_name',
            'last_name',
            'phone',
            'role',
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    # ---- Validation -------------------------------------------------------

    def validate_email(self, value):
        email = value.lower().strip()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                'A user with this email address already exists.'
            )
        return email

    def validate_username(self, value):
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                'This username is already taken.'
            )
        return value.strip()

    def validate_role(self, value):
        if value not in ['user', 'agent']:
            raise serializers.ValidationError('You can only register as a user or an agent.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Passwords do not match. Please try again.'}
            )
        return attrs

    # ---- Create -----------------------------------------------------------

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        # Generate verification token
        verification_token = str(uuid.uuid4()).replace('-', '')

        user = CustomUser(
            verification_token=verification_token,
            **validated_data,
        )
        user.set_password(password)
        user.is_active = True        # account active but unverified
        user.is_verified = False
        user.save()

        # Send verification email (signal also fires, but we send here too
        # so the serializer can be used independently of signals).
        self._send_verification_email(user)

        return user

    def _send_verification_email(self, user):
        """Send an account verification email to the new user."""
        try:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
            verify_url = f"{frontend_url}/accounts/verify-email/{user.verification_token}/"

            context = {
                'user': user,
                'verify_url': verify_url,
                'site_name': 'Lands and Houses',
            }

            # Try to render HTML template; fall back to plain text if template missing.
            try:
                html_message = render_to_string(
                    'accounts/emails/verification_email.html', context
                )
                plain_message = strip_tags(html_message)
            except Exception:
                plain_message = (
                    f"Hi {user.first_name},\n\n"
                    f"Welcome to Lands and Houses!\n\n"
                    f"Please verify your email address by clicking the link below:\n"
                    f"{verify_url}\n\n"
                    f"If you did not register, please ignore this email.\n\n"
                    f"Regards,\nLands and Houses Team"
                )
                html_message = None

            send_mail(
                subject='Verify Your Email – Lands and Houses',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning(
                'Failed to send verification email to %s: %s', user.email, exc
            )


# ---------------------------------------------------------------------------
# UserLoginSerializer
# ---------------------------------------------------------------------------

class UserLoginSerializer(serializers.Serializer):
    """
    Validates email + password credentials using Django's authenticate().
    Returns the authenticated user instance on success.
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password', '')

        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')

        # authenticate() uses USERNAME_FIELD which is 'email' for CustomUser
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )

        if user is None:
            raise AuthenticationFailed(
                'Invalid email or password. Please check your credentials.'
            )

        if user.is_suspended:
            raise AuthenticationFailed(
                'Your account has been suspended. Please contact support.'
            )

        if not user.is_active:
            raise AuthenticationFailed(
                'Your account is inactive. Please contact support.'
            )

        attrs['user'] = user
        return attrs


# ---------------------------------------------------------------------------
# UserProfileSerializer
# ---------------------------------------------------------------------------

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Full profile serializer. Exposes all non-sensitive CustomUser fields.
    Password fields are excluded. Avatar returns an absolute URL.
    """

    full_name = serializers.SerializerMethodField(read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True, write_only=False)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'bio',
            'avatar',
            'avatar_url',
            'role',
            'is_verified',
            'is_suspended',
            'last_seen',
            'date_joined',
        ]
        read_only_fields = [
            'id',
            'email',
            'role',
            'is_verified',
            'is_suspended',
            'last_seen',
            'date_joined',
        ]

    def get_full_name(self, obj):
        return obj.full_name

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None

    def update(self, instance, validated_data):
        # Handle avatar upload – remove old file if replaced
        new_avatar = validated_data.get('avatar')
        if new_avatar and instance.avatar:
            try:
                instance.avatar.delete(save=False)
            except Exception:
                pass
        return super().update(instance, validated_data)


# ---------------------------------------------------------------------------
# ChangePasswordSerializer
# ---------------------------------------------------------------------------

class ChangePasswordSerializer(serializers.Serializer):
    """
    Validates the old password before allowing the user to set a new one.
    Applies Django's built-in password validators to the new password.
    """

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        label='Confirm New Password',
        style={'input_type': 'password'},
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                'Your current password is incorrect.'
            )
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password2': 'New passwords do not match.'}
            )
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {'new_password': 'New password must differ from your current password.'}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


# ---------------------------------------------------------------------------
# PasswordResetRequestSerializer
# ---------------------------------------------------------------------------

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Accepts an email address and initiates a password-reset flow.
    Always returns success (to avoid user-enumeration attacks).
    """

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower().strip()

    def save(self, **kwargs):
        from django.utils import timezone
        from datetime import timedelta

        email = self.validated_data['email']

        try:
            user = CustomUser.objects.get(email__iexact=email, is_active=True)
        except CustomUser.DoesNotExist:
            # Silently return to prevent user enumeration
            return

        # Generate a reset token and set expiry (1 hour)
        token = str(uuid.uuid4()).replace('-', '')
        user.password_reset_token = token
        user.password_reset_expiry = timezone.now() + timedelta(hours=1)
        user.save(update_fields=['password_reset_token', 'password_reset_expiry'])

        self._send_reset_email(user, token)

    def _send_reset_email(self, user, token):
        """Send the password-reset email."""
        try:
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
            reset_url = (
                f"{frontend_url}/accounts/password-reset/confirm/{token}/"
            )

            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': 'Lands and Houses',
                'expiry_hours': 1,
            }

            try:
                html_message = render_to_string(
                    'accounts/emails/password_reset_email.html', context
                )
                plain_message = strip_tags(html_message)
            except Exception:
                plain_message = (
                    f"Hi {user.first_name},\n\n"
                    f"You requested a password reset for your Lands and Houses account.\n\n"
                    f"Click the link below to reset your password (valid for 1 hour):\n"
                    f"{reset_url}\n\n"
                    f"If you did not request this, please ignore this email.\n\n"
                    f"Regards,\nLands and Houses Team"
                )
                html_message = None

            send_mail(
                subject='Password Reset Request – Lands and Houses',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as exc:
            logger.warning(
                'Failed to send password reset email to %s: %s', user.email, exc
            )


# ---------------------------------------------------------------------------
# PasswordResetConfirmSerializer
# ---------------------------------------------------------------------------

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Validates a password-reset token and sets the new password.
    Token must not be expired and must match a real user record.
    """

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        validators=[validate_password],
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        label='Confirm New Password',
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        from django.utils import timezone

        token = attrs.get('token', '').strip()

        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError(
                {'new_password2': 'Passwords do not match.'}
            )

        try:
            user = CustomUser.objects.get(
                password_reset_token=token,
                is_active=True,
            )
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError(
                {'token': 'Invalid or expired password-reset link.'}
            )

        if user.password_reset_expiry and user.password_reset_expiry < timezone.now():
            raise serializers.ValidationError(
                {'token': 'This password-reset link has expired. Please request a new one.'}
            )

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.password_reset_token = ''
        user.password_reset_expiry = None
        user.save(update_fields=['password', 'password_reset_token', 'password_reset_expiry'])
        return user
