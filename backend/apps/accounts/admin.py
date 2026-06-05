"""
Accounts app Django admin configuration - Lands and Houses
Registers CustomUser and UserActivity with rich admin customisation.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, UserActivity


# ---------------------------------------------------------------------------
# Custom admin actions
# ---------------------------------------------------------------------------

@admin.action(description='Suspend selected users')
def suspend_users(modeladmin, request, queryset):
    """Mark selected users as suspended (blocks login)."""
    updated = queryset.exclude(role='super_admin').update(is_suspended=True)
    modeladmin.message_user(
        request,
        f'{updated} user(s) suspended successfully.',
    )


@admin.action(description='Activate / un-suspend selected users')
def activate_users(modeladmin, request, queryset):
    """Remove the suspension flag from selected users."""
    updated = queryset.update(is_suspended=False)
    modeladmin.message_user(
        request,
        f'{updated} user(s) reactivated successfully.',
    )


@admin.action(description='Promote selected users to Admin role')
def make_admin(modeladmin, request, queryset):
    """Elevate selected regular users to the admin role."""
    updated = queryset.filter(role='user').update(role='admin')
    modeladmin.message_user(
        request,
        f'{updated} user(s) promoted to Admin.',
    )


@admin.action(description='Demote selected admins to User role')
def make_user(modeladmin, request, queryset):
    """Revert selected admins back to standard user role."""
    updated = queryset.filter(role='admin').update(role='user')
    modeladmin.message_user(
        request,
        f'{updated} admin(s) demoted to User.',
    )


@admin.action(description='Mark selected users as email-verified')
def verify_users(modeladmin, request, queryset):
    """Manually mark selected users as email-verified."""
    updated = queryset.update(is_verified=True, verification_token='')
    modeladmin.message_user(
        request,
        f'{updated} user(s) marked as verified.',
    )


# ---------------------------------------------------------------------------
# CustomUserAdmin
# ---------------------------------------------------------------------------

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Full-featured Django admin for CustomUser.
    Inherits UserAdmin to keep the password hashing / change form intact.
    """

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------

    list_display = [
        'avatar_thumbnail',
        'email',
        'username',
        'full_name_display',
        'role',
        'is_verified',
        'is_suspended',
        'is_active',
        'date_joined',
        'last_seen',
    ]
    list_display_links = ['email', 'username']
    list_filter = [
        'role',
        'is_verified',
        'is_suspended',
        'is_active',
        'is_staff',
        'date_joined',
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    date_hierarchy = 'date_joined'
    actions = [suspend_users, activate_users, make_admin, make_user, verify_users]

    # ------------------------------------------------------------------
    # Detail / edit view
    # ------------------------------------------------------------------

    # Override the default fieldsets from UserAdmin to include our extra fields
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        (
            _('Personal Info'),
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'phone',
                    'bio',
                    'avatar',
                )
            },
        ),
        (
            _('Roles & Status'),
            {
                'fields': (
                    'role',
                    'is_verified',
                    'is_suspended',
                    'is_active',
                    'is_staff',
                    'is_superuser',
                )
            },
        ),
        (
            _('Verification & Reset Tokens'),
            {
                'classes': ('collapse',),
                'fields': (
                    'verification_token',
                    'password_reset_token',
                    'password_reset_expiry',
                ),
            },
        ),
        (
            _('Permissions'),
            {
                'classes': ('collapse',),
                'fields': ('groups', 'user_permissions'),
            },
        ),
        (
            _('Important Dates'),
            {'fields': ('last_login', 'last_seen', 'date_joined')},
        ),
    )

    # Fieldsets used when adding a brand-new user
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'username',
                    'first_name',
                    'last_name',
                    'phone',
                    'role',
                    'password1',
                    'password2',
                ),
            },
        ),
    )

    readonly_fields = ['date_joined', 'last_login', 'last_seen']

    # ------------------------------------------------------------------
    # Custom display helpers
    # ------------------------------------------------------------------

    @admin.display(description='Name', ordering='first_name')
    def full_name_display(self, obj):
        return obj.get_full_name() or obj.username

    @admin.display(description='Avatar')
    def avatar_thumbnail(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;'
                'border-radius:50%;object-fit:cover;" />',
                obj.avatar.url,
            )
        return format_html(
            '<span style="display:inline-block;width:36px;height:36px;'
            'border-radius:50%;background:#dee2e6;line-height:36px;'
            'text-align:center;font-size:14px;">👤</span>'
        )

    # Make boolean columns show pretty icons
    @admin.display(boolean=True, description='Verified', ordering='is_verified')
    def is_verified_icon(self, obj):
        return obj.is_verified

    @admin.display(boolean=True, description='Suspended', ordering='is_suspended')
    def is_suspended_icon(self, obj):
        return obj.is_suspended


# ---------------------------------------------------------------------------
# UserActivityAdmin
# ---------------------------------------------------------------------------

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """Read-only admin view of user activity log entries."""

    list_display = [
        'user_email',
        'action',
        'description_short',
        'ip_address',
        'timestamp',
    ]
    list_filter = ['action', 'timestamp']
    search_fields = ['user__email', 'user__username', 'description', 'ip_address']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'timestamp']

    def has_add_permission(self, request):
        """Activity records are created programmatically; block manual creation."""
        return False

    def has_change_permission(self, request, obj=None):
        """Activity records are immutable audit logs."""
        return False

    @admin.display(description='User', ordering='user__email')
    def user_email(self, obj):
        return obj.user.email if obj.user else '—'

    @admin.display(description='Description')
    def description_short(self, obj):
        if obj.description and len(obj.description) > 80:
            return obj.description[:80] + '…'
        return obj.description or '—'
