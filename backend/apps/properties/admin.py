"""Properties admin"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Property, PropertyImage, PropertyVideo, Amenity, SavedProperty, PropertyView


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 3
    fields = ['image', 'caption', 'is_primary', 'order', 'preview']
    readonly_fields = ['preview']

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="80" style="border-radius:4px"/>', obj.image.url)
        return 'No image'


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ['title', 'property_type', 'listing_type', 'status', 'city', 'state', 'price', 'is_featured', 'is_active', 'view_count']
    list_filter = ['status', 'property_type', 'listing_type', 'is_featured', 'is_active', 'state']
    search_fields = ['title', 'city', 'state', 'address']
    list_editable = ['status', 'is_featured', 'is_active']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PropertyImageInline]
    filter_horizontal = ['amenities']
    ordering = ['-created_at']


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon']


@admin.register(SavedProperty)
class SavedPropertyAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'saved_at']
    search_fields = ['user__email', 'property__title']
