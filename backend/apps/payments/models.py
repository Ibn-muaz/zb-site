"""Payments app models"""
from django.db import models
from django.conf import settings
import uuid


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    TYPE_CHOICES = [
        ('booking_fee', 'Booking Fee'),
        ('inspection_fee', 'Inspection Fee'),
        ('deposit', 'Deposit'),
        ('full_payment', 'Full Payment'),
        ('agency_fee', 'Agency Fee'),
        ('verification_fee', 'Agent Verification Fee'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    property = models.ForeignKey('properties.Property', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='payments')
    negotiation = models.ForeignKey('negotiations.Negotiation', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Stripe
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    stripe_client_secret = models.CharField(max_length=500, blank=True)

    # Meta
    description = models.TextField(blank=True)
    receipt_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {str(self.id)[:8]} - {self.amount} {self.currency} [{self.status}]"
