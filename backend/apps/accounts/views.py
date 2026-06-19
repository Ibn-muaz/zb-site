"""
Accounts app views - Lands and Houses
Class-based views (DRF APIView + Django TemplateView) for authentication,
profile management, and user/admin dashboards.
"""
import logging
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Count, Sum, Q

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import CustomUser, UserActivity
from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    UserMiniSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client_ip(request):
    """Return the real client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _log_activity(user, action, description='', ip_address=None):
    """Create a UserActivity record safely (non-blocking)."""
    try:
        UserActivity.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip_address,
        )
    except Exception as exc:
        logger.warning('UserActivity log failed: %s', exc)


def _get_tokens_for_user(user):
    """Generate a JWT refresh + access token pair for the given user."""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ---------------------------------------------------------------------------
# RegisterView
# ---------------------------------------------------------------------------

@method_decorator(ensure_csrf_cookie, name='dispatch')
class RegisterView(TemplateView):
    """
    GET  → renders the registration HTML page.
    POST → handled by DRF (JSON) via the same URL; creates user, returns tokens.
    """

    template_name = 'accounts/register.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Create Your Account'
        return ctx

    def post(self, request, *args, **kwargs):
        """Handle JSON registration requests from the frontend form."""
        serializer = UserRegisterSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.save()
            tokens = _get_tokens_for_user(user)
            ip = _get_client_ip(request)
            _log_activity(user, 'register', 'New account registered', ip)

            return Response(
                {
                    'message': (
                        'Registration successful! '
                        'Please check your email to verify your account.'
                    ),
                    'user': UserMiniSerializer(
                        user, context={'request': request}
                    ).data,
                    'tokens': tokens,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LoginView
# ---------------------------------------------------------------------------

@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginView(TemplateView):
    """
    GET  → renders the login HTML page.
    POST → validates credentials, returns JWT tokens, sets Django session.
    """

    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Sign In to Your Account'
        ctx['next'] = self.request.GET.get('next', '')
        return ctx

    def post(self, request, *args, **kwargs):
        serializer = UserLoginSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            user = serializer.validated_data['user']

            # Establish Django session (for template views)
            auth_login(request, user)

            # Update last_seen
            user.last_seen = timezone.now()
            user.save(update_fields=['last_seen'])

            tokens = _get_tokens_for_user(user)
            ip = _get_client_ip(request)
            _log_activity(user, 'login', f'Login from IP {ip}', ip)

            next_url = request.data.get('next')
            if not next_url:
                if user.is_admin:
                    next_url = '/admin-panel/'
                elif user.is_agent:
                    next_url = '/admin-panel/properties/'
                else:
                    next_url = '/dashboard/'

            return Response(
                {
                    'message': f'Welcome back, {user.first_name}!',
                    'user': UserMiniSerializer(
                        user, context={'request': request}
                    ).data,
                    'tokens': tokens,
                    'redirect': next_url,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LogoutView
# ---------------------------------------------------------------------------

class LogoutView(APIView):
    """
    POST → blacklists the refresh token, clears Django session.
    Works for both JWT-only and session-based flows.
    """

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        ip = _get_client_ip(request)

        # Blacklist the JWT refresh token if provided
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError as exc:
                logger.debug('Logout token blacklist skipped: %s', exc)

        # Log activity before clearing session
        if request.user and request.user.is_authenticated:
            _log_activity(request.user, 'logout', f'Logout from IP {ip}', ip)

        # Clear Django session
        auth_logout(request)

        return Response(
            {'message': 'You have been successfully logged out.'},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# EmailVerifyView
# ---------------------------------------------------------------------------

class EmailVerifyView(APIView):
    """
    GET /accounts/verify-email/<token>/
    Verifies the user's email address by checking the verification token.
    """

    permission_classes = [AllowAny]

    def get(self, request, token, *args, **kwargs):
        if not token:
            return Response(
                {'error': 'Invalid verification link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(
                verification_token=token, is_active=True
            )
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'This verification link is invalid or has already been used.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return Response(
                {'message': 'Your email has already been verified. You can now log in.'},
                status=status.HTTP_200_OK,
            )

        user.is_verified = True
        user.verification_token = ''
        user.save(update_fields=['is_verified', 'verification_token'])

        ip = _get_client_ip(request)
        _log_activity(user, 'register', 'Email verified', ip)

        # For web requests, redirect to login with a success message
        if 'text/html' in request.accepted_media_type:
            messages.success(
                request,
                'Your email has been verified! You can now log in.',
            )
            return redirect('accounts:login')

        return Response(
            {
                'message': (
                    'Email verified successfully! '
                    'Your account is now fully active.'
                )
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# PasswordResetRequestView
# ---------------------------------------------------------------------------

class PasswordResetRequestView(APIView):
    """
    POST /accounts/password-reset/
    Accepts an email, generates a reset token, and sends a reset email.
    Always returns 200 to prevent user enumeration.
    """

    permission_classes = [AllowAny]
    throttle_scope = 'anon'

    def get(self, request, *args, **kwargs):
        """Render the password-reset request template (for TemplateView mixin)."""
        from django.shortcuts import render
        return render(request, 'accounts/password_reset.html', {'page_title': 'Reset Password'})

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': (
                        'If an account with that email exists, '
                        'a password-reset link has been sent.'
                    )
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# PasswordResetConfirmView
# ---------------------------------------------------------------------------

class PasswordResetConfirmView(APIView):
    """
    GET  /accounts/password-reset/confirm/<token>/  → renders confirm page.
    POST /accounts/password-reset/confirm/<token>/  → sets the new password.
    """

    permission_classes = [AllowAny]

    def get(self, request, token, *args, **kwargs):
        from django.shortcuts import render
        # Validate token exists before rendering the form
        try:
            user = CustomUser.objects.get(
                password_reset_token=token, is_active=True
            )
            token_valid = (
                user.password_reset_expiry is None
                or user.password_reset_expiry >= timezone.now()
            )
        except CustomUser.DoesNotExist:
            token_valid = False

        return render(
            request,
            'accounts/password_reset_confirm.html',
            {
                'page_title': 'Set New Password',
                'token': token,
                'token_valid': token_valid,
            },
        )

    def post(self, request, token, *args, **kwargs):
        data = request.data.copy()
        data['token'] = token
        serializer = PasswordResetConfirmSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            ip = _get_client_ip(request)
            _log_activity(user, 'login', 'Password reset completed', ip)
            return Response(
                {'message': 'Your password has been reset successfully. You can now log in.'},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ProfileView
# ---------------------------------------------------------------------------

class ProfileView(APIView):
    """
    GET    /accounts/profile/  → returns the authenticated user's full profile.
    PUT    /accounts/profile/  → full update of profile fields.
    PATCH  /accounts/profile/  → partial update (e.g. avatar upload).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request, *args, **kwargs):
        serializer = UserProfileSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self._update(request, partial=False)

    def patch(self, request, *args, **kwargs):
        return self._update(request, partial=True)

    def _update(self, request, partial):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=partial,
            context={'request': request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Profile updated successfully.',
                    'user': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ChangePasswordView
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    """
    POST /accounts/change-password/
    Validates old password, then sets the new password.
    Rotates JWT tokens so the old access token is invalidated.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()

            # Issue fresh JWT tokens so the client doesn't get kicked out
            tokens = _get_tokens_for_user(request.user)
            ip = _get_client_ip(request)
            _log_activity(
                request.user, 'login', 'Password changed by user', ip
            )
            return Response(
                {
                    'message': 'Password changed successfully.',
                    'tokens': tokens,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# UserDashboardView
# ---------------------------------------------------------------------------

class UserDashboardView(LoginRequiredMixin, TemplateView):
    """
    GET /dashboard/
    Renders the user dashboard showing saved properties, recent views,
    active negotiations, and recent payments.
    """

    template_name = 'accounts/dashboard.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Lazy imports to avoid circular deps
        from apps.properties.models import SavedProperty, PropertyView
        from apps.negotiations.models import Negotiation
        from apps.payments.models import Payment

        saved_properties = (
            SavedProperty.objects.filter(user=user)
            .select_related('property')
            .prefetch_related('property__images')
            .order_by('-saved_at')[:6]
        )

        recent_views = (
            PropertyView.objects.filter(user=user)
            .select_related('property')
            .prefetch_related('property__images')
            .order_by('-viewed_at')
            .distinct()[:6]
        )

        active_negotiations = (
            Negotiation.objects.filter(
                user=user,
                status__in=['pending', 'counter_offered'],
            )
            .select_related('property')
            .prefetch_related('property__images')
            .order_by('-updated_at')[:5]
        )

        recent_payments = (
            Payment.objects.filter(user=user)
            .select_related('property')
            .order_by('-created_at')[:5]
        )

        # Summary stats
        stats = {
            'saved_count': SavedProperty.objects.filter(user=user).count(),
            'views_count': PropertyView.objects.filter(user=user).count(),
            'negotiations_count': Negotiation.objects.filter(user=user).count(),
            'payments_count': Payment.objects.filter(
                user=user, status='completed'
            ).count(),
        }

        recent_activity = (
            UserActivity.objects.filter(user=user).order_by('-timestamp')[:10]
        )

        ctx.update(
            {
                'page_title': f"Dashboard – {user.first_name}",
                'saved_properties': saved_properties,
                'recent_views': recent_views,
                'active_negotiations': active_negotiations,
                'recent_payments': recent_payments,
                'stats': stats,
                'recent_activity': recent_activity,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# Admin Panel Views  (role-restricted; NOT Django's built-in admin)
# ---------------------------------------------------------------------------

class AdminRequiredMixin(LoginRequiredMixin):
    """Mixin that restricts access to admin or super_admin role users."""

    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_admin:
            messages.error(request, 'You do not have permission to access this area.')
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)

class AdminOrAgentRequiredMixin(LoginRequiredMixin):
    """Mixin that restricts access to admin or agent role users."""

    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin or request.user.is_agent):
            messages.error(request, 'You do not have permission to access this area.')
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Main admin panel landing page with platform-wide analytics."""

    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        from apps.properties.models import Property
        from apps.negotiations.models import Negotiation
        from apps.payments.models import Payment

        stats = {
            'total_users': CustomUser.objects.filter(role='user').count(),
            'verified_users': CustomUser.objects.filter(
                role='user', is_verified=True
            ).count(),
            'total_properties': Property.objects.count(),
            'active_properties': Property.objects.filter(
                is_active=True, status='available'
            ).count(),
            'total_negotiations': Negotiation.objects.count(),
            'pending_negotiations': Negotiation.objects.filter(
                status='pending'
            ).count(),
            'total_payments': Payment.objects.filter(
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or 0,
        }

        recent_users = CustomUser.objects.order_by('-date_joined')[:5]
        recent_negotiations = (
            Negotiation.objects.select_related('user', 'listing').order_by(
                '-created_at'
            )[:5]
        )

        ctx.update(
            {
                'page_title': 'Admin Dashboard',
                'stats': stats,
                'recent_users': recent_users,
                'recent_negotiations': recent_negotiations,
            }
        )
        return ctx


class AdminPropertyListView(AdminOrAgentRequiredMixin, TemplateView):
    """Paginated list of all properties for admin management."""

    template_name = 'admin_panel/properties/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.properties.models import Property

        properties = Property.objects.select_related('admin').prefetch_related(
            'images'
        ).order_by('-created_at')

        if self.request.user.is_agent:
            properties = properties.filter(admin=self.request.user)

        # Simple search
        query = self.request.GET.get('q', '')
        if query:
            properties = properties.filter(
                Q(title__icontains=query)
                | Q(city__icontains=query)
                | Q(state__icontains=query)
            )

        ctx.update(
            {
                'page_title': 'Manage Properties',
                'properties': properties,
                'search_query': query,
            }
        )
        return ctx


class AdminPropertyCreateView(AdminOrAgentRequiredMixin, TemplateView):
    """Render the property creation form."""

    template_name = 'admin_panel/properties/create.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_agent and not request.user.is_verified:
            messages.warning(request, "You must pay the verification fee before listing properties.")
            from django.shortcuts import redirect
            return redirect('/payments/checkout/?type=verification_fee')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Add New Property'
        return ctx


class AdminPropertyEditView(AdminOrAgentRequiredMixin, TemplateView):
    """Render the property edit form for a specific property slug."""

    template_name = 'admin_panel/properties/edit.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.properties.models import Property

        prop = get_object_or_404(Property, slug=kwargs.get('slug'))
        if self.request.user.is_agent and prop.admin != self.request.user:
            messages.error(self.request, 'You do not have permission to edit this property.')
            from django.shortcuts import redirect
            return redirect('admin_panel:property-list')
        ctx.update({'page_title': f'Edit: {prop.title}', 'property': prop})
        return ctx


class AdminPropertyDeleteView(AdminOrAgentRequiredMixin, APIView):
    """DELETE /admin-panel/properties/<slug>/delete/ – soft-deletes a property."""

    def post(self, request, slug, *args, **kwargs):
        from apps.properties.models import Property

        prop = get_object_or_404(Property, slug=slug)
        if request.user.is_agent and prop.admin != request.user:
            return Response(
                {'error': 'You do not have permission to delete this property.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        title = prop.title
        prop.is_active = False
        prop.save(update_fields=['is_active'])
        return Response(
            {'message': f'Property "{title}" has been deactivated.'},
            status=status.HTTP_200_OK,
        )


class AdminUserListView(AdminRequiredMixin, TemplateView):
    """Paginated list of all registered users."""

    template_name = 'admin_panel/users/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        users = CustomUser.objects.all().order_by('-date_joined')
        query = self.request.GET.get('q', '')
        role_filter = self.request.GET.get('role', '')

        if query:
            users = users.filter(
                Q(email__icontains=query)
                | Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )
        if role_filter:
            users = users.filter(role=role_filter)

        ctx.update(
            {
                'page_title': 'Manage Users',
                'users': users,
                'search_query': query,
                'role_filter': role_filter,
            }
        )
        return ctx


class AdminSuspendUserView(AdminRequiredMixin, APIView):
    """Toggle user suspension status."""

    def post(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(CustomUser, id=user_id)

        # Prevent suspending super admins
        if user.is_super_admin:
            return Response(
                {'error': 'Cannot suspend a super admin account.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user.is_suspended = not user.is_suspended
        user.save(update_fields=['is_suspended'])
        action = 'suspended' if user.is_suspended else 'reactivated'
        return Response(
            {'message': f'User {user.email} has been {action}.', 'is_suspended': user.is_suspended},
            status=status.HTTP_200_OK,
        )


class AdminNegotiationListView(AdminRequiredMixin, TemplateView):
    """List all negotiations for admin review."""

    template_name = 'admin_panel/negotiations/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.negotiations.models import Negotiation

        negotiations = (
            Negotiation.objects.select_related('user', 'listing', 'handled_by')
            .order_by('-created_at')
        )
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            negotiations = negotiations.filter(status=status_filter)

        ctx.update(
            {
                'page_title': 'Manage Negotiations',
                'negotiations': negotiations,
                'status_filter': status_filter,
            }
        )
        return ctx


class AdminNegotiationDetailView(AdminRequiredMixin, TemplateView):
    """Detail view of a single negotiation thread."""

    template_name = 'admin_panel/negotiations/detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.negotiations.models import Negotiation

        negotiation = get_object_or_404(
            Negotiation.objects.select_related('user', 'listing', 'handled_by').prefetch_related('messages'),
            id=kwargs.get('negotiation_id'),
        )
        ctx.update(
            {
                'page_title': f'Negotiation – {negotiation.listing.title}',
                'negotiation': negotiation,
            }
        )
        return ctx


class AdminContentView(AdminRequiredMixin, TemplateView):
    """CMS content management panel."""

    template_name = 'admin_panel/content/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Content Management'
        return ctx


class AdminPaymentListView(AdminRequiredMixin, TemplateView):
    """Paginated payment transaction list."""

    template_name = 'admin_panel/payments/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.payments.models import Payment

        payments = Payment.objects.select_related(
            'user', 'property', 'negotiation'
        ).order_by('-created_at')

        status_filter = self.request.GET.get('status', '')
        if status_filter:
            payments = payments.filter(status=status_filter)

        total_revenue = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0

        ctx.update(
            {
                'page_title': 'Payment Transactions',
                'payments': payments,
                'total_revenue': total_revenue,
                'status_filter': status_filter,
            }
        )
        return ctx


class AdminAnalyticsView(AdminRequiredMixin, TemplateView):
    """Platform analytics and reporting view."""

    template_name = 'admin_panel/analytics.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.properties.models import Property, PropertyView
        from apps.negotiations.models import Negotiation
        from apps.payments.models import Payment
        from django.db.models.functions import TruncMonth

        # Monthly registration trend (last 12 months)
        monthly_users = (
            CustomUser.objects.filter(role='user')
            .annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Monthly revenue
        monthly_revenue = (
            Payment.objects.filter(status='completed')
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        # Top viewed properties
        top_properties = (
            Property.objects.annotate(view_count_ann=Count('views'))
            .order_by('-view_count_ann')[:10]
        )

        ctx.update(
            {
                'page_title': 'Analytics & Reports',
                'monthly_users': list(monthly_users),
                'monthly_revenue': list(monthly_revenue),
                'top_properties': top_properties,
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# User Dashboard Sub-Views
# ---------------------------------------------------------------------------

class UserSavedPropertiesView(LoginRequiredMixin, TemplateView):
    """Dashboard page listing all of the user's saved / bookmarked properties."""

    template_name = 'accounts/saved_properties.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.properties.models import SavedProperty

        saved = (
            SavedProperty.objects.filter(user=self.request.user)
            .select_related('property')
            .prefetch_related('property__images')
            .order_by('-saved_at')
        )
        ctx.update({'page_title': 'Saved Properties', 'saved_properties': saved})
        return ctx


class UserNegotiationsView(LoginRequiredMixin, TemplateView):
    """Dashboard page listing the user's negotiations."""

    template_name = 'accounts/my_negotiations.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.negotiations.models import Negotiation

        negotiations = (
            Negotiation.objects.filter(user=self.request.user)
            .select_related('listing')
            .prefetch_related('listing__images', 'messages')
            .order_by('-created_at')
        )
        ctx.update({'page_title': 'My Negotiations', 'negotiations': negotiations})
        return ctx


class UserPaymentsView(LoginRequiredMixin, TemplateView):
    """Dashboard page listing the user's payment history."""

    template_name = 'accounts/my_payments.html'
    login_url = '/accounts/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.payments.models import Payment

        payments = (
            Payment.objects.filter(user=self.request.user)
            .select_related('property')
            .order_by('-created_at')
        )
        total_paid = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0

        ctx.update(
            {
                'page_title': 'Payment History',
                'payments': payments,
                'total_paid': total_paid,
            }
        )
        return ctx

# ── API aliases for the DRF router ──
RegisterAPIView = RegisterView
LoginAPIView = LoginView
LogoutAPIView = LogoutView
ProfileAPIView = ProfileView
ChangePasswordAPIView = ChangePasswordView
