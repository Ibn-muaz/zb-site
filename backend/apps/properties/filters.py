"""Properties filter"""
import django_filters
from .models import Property


class PropertyFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    city = django_filters.CharFilter(field_name='city', lookup_expr='icontains')
    state = django_filters.CharFilter(field_name='state', lookup_expr='icontains')
    bedrooms_min = django_filters.NumberFilter(field_name='bedrooms', lookup_expr='gte')
    bedrooms_max = django_filters.NumberFilter(field_name='bedrooms', lookup_expr='lte')
    bathrooms_min = django_filters.NumberFilter(field_name='bathrooms', lookup_expr='gte')
    area_min = django_filters.NumberFilter(field_name='area_sqft', lookup_expr='gte')
    area_max = django_filters.NumberFilter(field_name='area_sqft', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Property
        fields = ['property_type', 'listing_type', 'status', 'is_featured']

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(city__icontains=value) |
            Q(state__icontains=value) |
            Q(address__icontains=value)
        )
