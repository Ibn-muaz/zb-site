"""ZB Lands and Home - URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

schema_view = get_schema_view(
    openapi.Info(
        title="ZB Lands and Home API",
        default_version='v1',
        description="RESTful API for ZB Lands and Home Real Estate Platform",
        terms_of_service="https://ZBLandsAndHome.com/terms/",
        contact=openapi.Contact(email="admin@ZBLandsAndHome.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Web pages
    path('', include('apps.content.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('properties/', include('apps.properties.urls')),
    path('negotiations/', include('apps.negotiations.urls')),
    path('payments/', include('apps.payments.urls')),
    path('dashboard/', include('apps.accounts.dashboard_urls', namespace='dashboard')),
    path('admin-panel/', include('apps.accounts.admin_urls', namespace='admin_panel')),

    # API
    path('api/v1/', include('api.v1.urls')),

    # API Docs
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
