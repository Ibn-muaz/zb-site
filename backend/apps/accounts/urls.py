"""
Accounts app URL patterns - Lands and Houses
Web-facing authentication and profile URLs.
"""
from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    NeonLoginView,
    LogoutView,
    EmailVerifyView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    ProfileView,
    ChangePasswordView,
)



urlpatterns = [
    # -----------------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------------

    # GET  → render registration page
    # POST → create account (JSON), returns JWT tokens
    path('register/', RegisterView.as_view(), name='register'),

    # GET  → render login page
    # POST → authenticate (JSON), returns JWT tokens + sets session
    path('login/', LoginView.as_view(), name='login'),

    # POST → authenticate via Neon Auth token
    path('neon-login/', NeonLoginView.as_view(), name='neon-login'),

    # POST → blacklist JWT refresh token, clear session
    path('logout/', LogoutView.as_view(), name='logout'),

    # -----------------------------------------------------------------------
    # Email Verification
    # -----------------------------------------------------------------------

    # GET  → verify email address via one-time token
    path(
        'verify-email/<str:token>/',
        EmailVerifyView.as_view(),
        name='verify-email',
    ),

    # -----------------------------------------------------------------------
    # Password Reset
    # -----------------------------------------------------------------------

    # GET  → render password-reset request form
    # POST → send reset link to email address
    path(
        'password-reset/',
        PasswordResetRequestView.as_view(),
        name='password-reset',
    ),

    # GET  → render the new-password form (token validated before render)
    # POST → set new password using the provided token
    path(
        'password-reset/confirm/<str:token>/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),

    # -----------------------------------------------------------------------
    # Profile & Password Change
    # -----------------------------------------------------------------------

    # GET   → retrieve authenticated user's profile
    # PUT   → full profile update
    # PATCH → partial profile update / avatar upload
    path('profile/', ProfileView.as_view(), name='profile'),

    # POST → change password (requires authentication)
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
