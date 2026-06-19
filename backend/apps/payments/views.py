"""Payments views — Stripe integration"""
import stripe
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView, ListView
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Payment
from apps.properties.models import Property
from apps.negotiations.models import Negotiation

stripe.api_key = settings.STRIPE_SECRET_KEY


@method_decorator(login_required, name='dispatch')
class PaymentCheckoutView(View):
    template_name = 'payments/checkout.html'

    def get(self, request, property_id=None):
        payment_type = request.GET.get('type', 'booking_fee')
        
        if payment_type == 'verification_fee':
            prop = None
            negotiation = None
            amount = 5000
        else:
            if not property_id:
                messages.error(request, 'Property ID is required for this payment.')
                return redirect('home')
            prop = get_object_or_404(Property, id=property_id, is_active=True)
            negotiation_id = request.GET.get('negotiation', None)
            negotiation = None
            if negotiation_id:
                try:
                    negotiation = Negotiation.objects.get(id=negotiation_id, user=request.user)
                except Negotiation.DoesNotExist:
                    pass

            amounts = {
                'booking_fee': min(float(prop.price) * 0.01, 500000),  # 1% or max 500k
                'inspection_fee': 15000,
                'agency_fee': float(prop.price) * 0.05,
                'deposit': float(prop.price) * 0.10,
            }
            amount = amounts.get(payment_type, 50000)

        ctx = {
            'property': prop,
            'negotiation': negotiation,
            'payment_type': payment_type,
            'amount': amount,
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        }
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name='dispatch')
class CreatePaymentIntentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        property_id = request.data.get('property_id')
        payment_type = request.data.get('payment_type', 'booking_fee')
        amount = request.data.get('amount')
        negotiation_id = request.data.get('negotiation_id')

        if payment_type == 'verification_fee':
            if not amount:
                return Response({'error': 'amount required.'}, status=status.HTTP_400_BAD_REQUEST)
            prop = None
            negotiation = None
            description = 'Agent Verification Fee'
            metadata = {
                'user_id': str(request.user.id),
                'payment_type': payment_type,
            }
        else:
            if not property_id or not amount:
                return Response({'error': 'property_id and amount required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                prop = Property.objects.get(id=property_id)
            except Property.DoesNotExist:
                return Response({'error': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)
                
            negotiation = None
            if negotiation_id:
                try:
                    negotiation = Negotiation.objects.get(id=negotiation_id, user=request.user)
                except Negotiation.DoesNotExist:
                    pass
            description = f'{payment_type.replace("_", " ").title()} for {prop.title}'
            metadata = {
                'user_id': str(request.user.id),
                'property_id': str(prop.id),
                'payment_type': payment_type,
            }

        try:
            amount_kobo = int(float(amount) * 100)  # Stripe uses smallest unit

            intent = stripe.PaymentIntent.create(
                amount=amount_kobo,
                currency='ngn',
                metadata=metadata
            )

            payment = Payment.objects.create(
                user=request.user,
                property=prop,
                negotiation=negotiation,
                payment_type=payment_type,
                amount=amount,
                currency='NGN',
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret,
                description=description,
            )

            return Response({
                'client_secret': intent.client_secret,
                'payment_id': str(payment.id),
            })
        except stripe.error.StripeError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(login_required, name='dispatch')
class PaymentSuccessView(TemplateView):
    template_name = 'payments/success.html'

    def get(self, request, *args, **kwargs):
        payment_id = request.GET.get('payment_id')
        payment = None
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id, user=request.user)
                if payment.status == 'pending':
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.save()

                    if payment.payment_type == 'verification_fee':
                        user = payment.user
                        user.is_verified = True
                        user.save(update_fields=['is_verified'])

            except Payment.DoesNotExist:
                pass
        return render(request, self.template_name, {'payment': payment})


@method_decorator(login_required, name='dispatch')
class PaymentCancelView(TemplateView):
    template_name = 'payments/cancel.html'


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            if settings.STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
            else:
                event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception as e:
            return HttpResponse(status=400)

        if event['type'] == 'payment_intent.succeeded':
            intent = event['data']['object']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=intent['id'])
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                payment.save()

                if payment.payment_type == 'verification_fee':
                    user = payment.user
                    user.is_verified = True
                    user.save(update_fields=['is_verified'])
                    title = 'Verification Successful'
                    message = 'You have successfully paid your verification fee and are now a verified agent.'
                else:
                    title = 'Payment Successful!'
                    message = f'Your payment of ₦{payment.amount:,.0f} for {payment.property.title} was successful.'

                from apps.notifications.views import create_notification
                create_notification(
                    user=payment.user,
                    notification_type='payment_success',
                    title=title,
                    message=message,
                    link='/dashboard/payments/',
                )
            except Payment.DoesNotExist:
                pass

        elif event['type'] == 'payment_intent.payment_failed':
            intent = event['data']['object']
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=intent['id'])
                payment.status = 'failed'
                payment.save()
            except Payment.DoesNotExist:
                pass

        return HttpResponse(status=200)


@method_decorator(login_required, name='dispatch')
class PaymentListView(ListView):
    template_name = 'payments/history.html'
    context_object_name = 'payments'

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related('property').order_by('-created_at')
