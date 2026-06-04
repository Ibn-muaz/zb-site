"""Payments admin"""
from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'property', 'payment_type', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'payment_type', 'currency']
    search_fields = ['user__email', 'property__title', 'stripe_payment_intent_id']
    readonly_fields = ['id', 'stripe_payment_intent_id', 'stripe_client_secret', 'created_at', 'updated_at']
    ordering = ['-created_at']
