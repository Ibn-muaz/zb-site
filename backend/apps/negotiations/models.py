"""Negotiations app models"""
from django.db import models
from django.conf import settings
import uuid


class Negotiation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('counter_offered', 'Counter Offered'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='negotiations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='negotiations')
    initial_offer = models.DecimalField(max_digits=15, decimal_places=2)
    current_offer = models.DecimalField(max_digits=15, decimal_places=2)
    counter_offer = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    asking_price = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='handled_negotiations')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Negotiation #{str(self.id)[:8]} - {self.listing.title} by {self.user}"

    def get_discount_percentage(self):
        if self.asking_price and self.current_offer:
            diff = self.asking_price - self.current_offer
            return round((float(diff) / float(self.asking_price)) * 100, 1)
        return 0


class NegotiationMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    negotiation = models.ForeignKey(Negotiation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    message_text = models.TextField()
    offer_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_admin_reply = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message in {self.negotiation} by {self.sender}"
