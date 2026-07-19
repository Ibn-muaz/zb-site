"""
Admin panel URL patterns - Lands and Houses
Custom admin panel mounted at /admin-panel/ (separate from Django's /admin/).
All views require admin or super_admin role.
"""
from django.urls import path
from .views import (
    AdminDashboardView,
    AdminUserListView,
    AdminUserCreateView,
    AdminUserEditView,
    AdminUserDeleteView,
    AdminSuspendUserView,
    AdminNegotiationListView,
    AdminNegotiationDetailView,
    AdminContentView,
    AdminPaymentListView,
    AdminAnalyticsView,
)
from apps.properties.views import (
    AdminPropertyListView,
    AdminPropertyCreateView,
    AdminPropertyEditView,
    AdminPropertyDeleteView,
)



app_name = 'admin_panel'

urlpatterns = [
    # -----------------------------------------------------------------------
    # Dashboard
    # -----------------------------------------------------------------------

    # GET → platform overview: KPI cards, recent users, recent negotiations
    path('', AdminDashboardView.as_view(), name='dashboard'),

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    # GET → paginated / searchable property list
    path('properties/', AdminPropertyListView.as_view(), name='property-list'),

    # GET  → blank property creation form
    # POST → handled by the API layer
    path('properties/add/', AdminPropertyCreateView.as_view(), name='property-create'),

    # GET  → pre-populated edit form for <slug>
    # POST → handled by the API layer
    path(
        'properties/<slug:slug>/edit/',
        AdminPropertyEditView.as_view(),
        name='property-edit',
    ),

    # POST → soft-delete (deactivate) property by slug
    path(
        'properties/<slug:slug>/delete/',
        AdminPropertyDeleteView.as_view(),
        name='property-delete',
    ),

    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------

    # GET → paginated / searchable user list with role filter
    path('users/', AdminUserListView.as_view(), name='user-list'),

    # GET / POST → Add new user/agent (Super Admin only)
    path('users/add/', AdminUserCreateView.as_view(), name='user-create'),

    # GET / POST → Edit user/agent (Super Admin only)
    path('users/<uuid:user_id>/edit/', AdminUserEditView.as_view(), name='user-edit'),

    # POST → Delete user/agent (Super Admin only)
    path('users/<uuid:user_id>/delete/', AdminUserDeleteView.as_view(), name='user-delete'),

    # POST → toggle is_suspended flag for user <id>
    path(
        'users/<uuid:user_id>/suspend/',
        AdminSuspendUserView.as_view(),
        name='user-suspend',
    ),

    # -----------------------------------------------------------------------
    # Negotiations
    # -----------------------------------------------------------------------

    # GET → list all negotiations with status filter
    path(
        'negotiations/',
        AdminNegotiationListView.as_view(),
        name='negotiation-list',
    ),

    # GET → full negotiation thread for a single negotiation
    path(
        'negotiations/<uuid:negotiation_id>/',
        AdminNegotiationDetailView.as_view(),
        name='negotiation-detail',
    ),

    # -----------------------------------------------------------------------
    # CMS Content
    # -----------------------------------------------------------------------

    # GET → CMS landing page (blog posts, FAQ, testimonials, site settings)
    path('content/', AdminContentView.as_view(), name='content'),

    # -----------------------------------------------------------------------
    # Payments
    # -----------------------------------------------------------------------

    # GET → paginated payment / transaction list with status filter
    path('payments/', AdminPaymentListView.as_view(), name='payment-list'),

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    # GET → charts and reports (user growth, revenue, top properties)
    path('analytics/', AdminAnalyticsView.as_view(), name='analytics'),
]
