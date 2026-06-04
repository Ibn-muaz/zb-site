"""Negotiations admin"""
from django.contrib import admin
from .models import Negotiation, NegotiationMessage


class NegotiationMessageInline(admin.TabularInline):
    model = NegotiationMessage
    extra = 0
    readonly_fields = ['sender', 'message_text', 'offer_amount', 'is_admin_reply', 'timestamp']


@admin.register(Negotiation)
class NegotiationAdmin(admin.ModelAdmin):
    list_display = ['listing', 'user', 'status', 'initial_offer', 'current_offer', 'counter_offer', 'created_at']
    list_filter = ['status']
    search_fields = ['listing__title', 'user__email']
    inlines = [NegotiationMessageInline]
    readonly_fields = ['id', 'created_at', 'updated_at']
    actions = ['mark_accepted', 'mark_rejected']

    @admin.action(description='Accept selected negotiations')
    def mark_accepted(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='accepted', resolved_at=timezone.now())

    @admin.action(description='Reject selected negotiations')
    def mark_rejected(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', resolved_at=timezone.now())
