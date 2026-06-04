"""API v1 URL router"""
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import RegisterAPIView, LoginAPIView, LogoutAPIView, ProfileAPIView, ChangePasswordAPIView
from apps.properties.views import (
    PropertyListAPIView, PropertyDetailAPIView, FeaturedPropertiesAPIView,
    SavePropertyAPIView, PropertySearchAPIView
)
from apps.negotiations.views import (
    NegotiationListAPIView, NegotiationDetailAPIView,
    CreateNegotiationAPIView, RespondNegotiationAPIView,
)
from apps.notifications.views import NotificationListAPIView, MarkNotificationReadAPIView

urlpatterns = [
    # Auth
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/profile/', ProfileAPIView.as_view(), name='api-profile'),
    path('auth/change-password/', ChangePasswordAPIView.as_view(), name='api-change-password'),

    # Properties
    path('properties/', PropertyListAPIView.as_view(), name='api-property-list'),
    path('properties/featured/', FeaturedPropertiesAPIView.as_view(), name='api-featured-properties'),
    path('properties/search/', PropertySearchAPIView.as_view(), name='api-property-search'),
    path('properties/<slug:slug>/', PropertyDetailAPIView.as_view(), name='api-property-detail'),
    path('properties/<slug:slug>/save/', SavePropertyAPIView.as_view(), name='api-save-property'),

    # Negotiations
    path('negotiations/', NegotiationListAPIView.as_view(), name='api-negotiation-list'),
    path('negotiations/create/', CreateNegotiationAPIView.as_view(), name='api-create-negotiation'),
    path('negotiations/<uuid:pk>/', NegotiationDetailAPIView.as_view(), name='api-negotiation-detail'),
    path('negotiations/<uuid:pk>/respond/', RespondNegotiationAPIView.as_view(), name='api-respond-negotiation'),

    # Notifications
    path('notifications/', NotificationListAPIView.as_view(), name='api-notifications'),
    path('notifications/read/', MarkNotificationReadAPIView.as_view(), name='api-mark-all-read'),
    path('notifications/<uuid:pk>/read/', MarkNotificationReadAPIView.as_view(), name='api-mark-read'),

    # Payments
    path('payments/', include('apps.payments.urls')),
]
