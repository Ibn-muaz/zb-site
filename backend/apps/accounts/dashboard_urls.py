"""
User dashboard URL patterns - Lands and Houses
Mounted at /dashboard/ in the root URL conf.
"""
from django.urls import path
from .views import (
    UserDashboardView,
    ProfileView,
    UserSavedPropertiesView,
    UserNegotiationsView,
    UserPaymentsView,
)



app_name = 'dashboard'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Dashboard home
    # -----------------------------------------------------------------------

    # GET → user dashboard overview (saved props, recent views, negotiations)
    path('', UserDashboardView.as_view(), name='home'),

    # -----------------------------------------------------------------------
    # Profile
    # -----------------------------------------------------------------------

    # GET   → profile page (template-rendered)
    # PUT   → full profile update
    # PATCH → partial profile / avatar update
    path('profile/', ProfileView.as_view(), name='profile'),

    # -----------------------------------------------------------------------
    # Saved Properties
    # -----------------------------------------------------------------------

    # GET → list of user's bookmarked / saved properties
    path('saved-properties/', UserSavedPropertiesView.as_view(), name='saved-properties'),

    # -----------------------------------------------------------------------
    # Negotiations
    # -----------------------------------------------------------------------

    # GET → list of user's offer / negotiation threads
    path('my-negotiations/', UserNegotiationsView.as_view(), name='my-negotiations'),

    # -----------------------------------------------------------------------
    # Payments
    # -----------------------------------------------------------------------

    # GET → user's payment / transaction history
    path('my-payments/', UserPaymentsView.as_view(), name='my-payments'),
]
