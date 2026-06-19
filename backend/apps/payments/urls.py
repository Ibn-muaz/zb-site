"""Payments URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('checkout/<uuid:property_id>/', views.PaymentCheckoutView.as_view(), name='payment-checkout'),
    path('checkout/', views.PaymentCheckoutView.as_view(), name='payment-checkout-general'),
    path('create-intent/', views.CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('success/', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('cancel/', views.PaymentCancelView.as_view(), name='payment-cancel'),
    path('webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    path('history/', views.PaymentListView.as_view(), name='payment-history'),
]
