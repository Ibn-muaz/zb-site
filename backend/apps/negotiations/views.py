"""Negotiations views"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated

from .models import Negotiation, NegotiationMessage
from .serializers import (
    NegotiationListSerializer, NegotiationDetailSerializer,
    CreateNegotiationSerializer, RespondNegotiationSerializer
)
from apps.properties.models import Property


# ──────────────────────── WEB VIEWS ────────────────────────

@method_decorator(login_required, name='dispatch')
class NegotiationListView(TemplateView):
    template_name = 'negotiations/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_admin:
            negotiations = Negotiation.objects.select_related('user', 'listing').order_by('-created_at')
        else:
            negotiations = Negotiation.objects.filter(user=user).select_related('listing').order_by('-created_at')
        ctx['negotiations'] = negotiations
        return ctx


@method_decorator(login_required, name='dispatch')
class NegotiationDetailView(View):
    template_name = 'negotiations/detail.html'

    def get(self, request, pk):
        neg = get_object_or_404(Negotiation, pk=pk)
        if not request.user.is_admin and neg.user != request.user:
            messages.error(request, 'Access denied.')
            return redirect('dashboard:my-negotiations')
        # Mark messages as read
        NegotiationMessage.objects.filter(
            negotiation=neg, is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        return render(request, self.template_name, {'negotiation': neg, 'messages_list': neg.messages.all()})

    def post(self, request, pk):
        neg = get_object_or_404(Negotiation, pk=pk)
        if not request.user.is_admin and neg.user != request.user:
            return redirect('home')
        if neg.status in ['accepted', 'rejected', 'completed']:
            messages.warning(request, 'This negotiation is already closed.')
            return redirect('negotiation-detail', pk=pk)

        msg_text = request.POST.get('message_text', '').strip()
        offer_amount = request.POST.get('offer_amount', None)
        action = request.POST.get('action', 'message')

        is_admin = request.user.is_admin

        if is_admin:
            if action == 'accept':
                neg.status = 'accepted'
                neg.resolved_at = timezone.now()
                neg.handled_by = request.user
                neg.save()
                NegotiationMessage.objects.create(
                    negotiation=neg, sender=request.user,
                    message_text=msg_text or 'Your offer has been accepted!',
                    is_admin_reply=True
                )
                messages.success(request, 'Offer accepted!')
            elif action == 'reject':
                neg.status = 'rejected'
                neg.resolved_at = timezone.now()
                neg.handled_by = request.user
                neg.save()
                NegotiationMessage.objects.create(
                    negotiation=neg, sender=request.user,
                    message_text=msg_text or 'We are unable to accept your offer at this time.',
                    is_admin_reply=True
                )
                messages.success(request, 'Offer rejected.')
            elif action == 'counter' and offer_amount:
                neg.status = 'counter_offered'
                neg.counter_offer = offer_amount
                neg.handled_by = request.user
                neg.save()
                NegotiationMessage.objects.create(
                    negotiation=neg, sender=request.user,
                    message_text=msg_text or f'We would like to counter-offer at ₦{float(offer_amount):,.0f}.',
                    offer_amount=offer_amount,
                    is_admin_reply=True
                )
                messages.success(request, 'Counter offer sent.')
            else:
                if msg_text:
                    NegotiationMessage.objects.create(
                        negotiation=neg, sender=request.user,
                        message_text=msg_text, is_admin_reply=True
                    )
        else:
            if offer_amount:
                neg.current_offer = offer_amount
                neg.status = 'pending'
                neg.save()
            if msg_text:
                NegotiationMessage.objects.create(
                    negotiation=neg, sender=request.user,
                    message_text=msg_text, offer_amount=offer_amount
                )

        return redirect('negotiation-detail', pk=pk)


@method_decorator(login_required, name='dispatch')
class CreateNegotiationView(View):
    def post(self, request, property_slug):
        prop = get_object_or_404(Property, slug=property_slug, is_active=True)
        if prop.status != 'available':
            messages.error(request, 'This property is not available.')
            return redirect('property-detail', slug=property_slug)

        offer_amount = request.POST.get('offer_amount', '').strip()
        message_text = request.POST.get('message_text', '').strip()

        if not offer_amount or not message_text:
            messages.error(request, 'Please provide both an offer amount and a message.')
            return redirect('property-detail', slug=property_slug)

        existing = Negotiation.objects.filter(
            user=request.user, listing=prop, status__in=['pending', 'counter_offered']
        ).first()
        if existing:
            messages.warning(request, 'You already have an active negotiation for this property.')
            return redirect('negotiation-detail', pk=existing.pk)

        neg = Negotiation.objects.create(
            listing=prop, user=request.user,
            initial_offer=offer_amount,
            current_offer=offer_amount,
            asking_price=prop.price,
            status='pending'
        )
        NegotiationMessage.objects.create(
            negotiation=neg, sender=request.user,
            message_text=message_text, offer_amount=offer_amount
        )
        messages.success(request, 'Your offer has been submitted! We will review and get back to you soon.')
        return redirect('negotiation-detail', pk=neg.pk)


@method_decorator(login_required, name='dispatch')
class AdminNegotiationDetailView(View):
    template_name = 'admin_panel/negotiation_detail.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        neg = get_object_or_404(Negotiation, pk=pk)
        NegotiationMessage.objects.filter(negotiation=neg, is_read=False).update(is_read=True)
        return render(request, self.template_name, {'negotiation': neg, 'messages_list': neg.messages.all()})

    def post(self, request, pk):
        neg = get_object_or_404(Negotiation, pk=pk)
        action = request.POST.get('action', '')
        msg_text = request.POST.get('message_text', '')
        counter_amount = request.POST.get('counter_offer_amount', None)

        if action == 'accept':
            neg.status = 'accepted'
            neg.resolved_at = timezone.now()
        elif action == 'reject':
            neg.status = 'rejected'
            neg.resolved_at = timezone.now()
        elif action == 'counter' and counter_amount:
            neg.status = 'counter_offered'
            neg.counter_offer = counter_amount

        neg.handled_by = request.user
        neg.save()

        if msg_text:
            NegotiationMessage.objects.create(
                negotiation=neg, sender=request.user,
                message_text=msg_text,
                offer_amount=counter_amount if action == 'counter' else None,
                is_admin_reply=True
            )
        messages.success(request, f'Negotiation {action}ed.')
        return redirect('admin_panel:negotiation-detail', negotiation_id=pk)


# ──────────────────────── REST API VIEWS ────────────────────────

class NegotiationListAPIView(generics.ListAPIView):
    serializer_class = NegotiationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            qs = Negotiation.objects.all()
        else:
            qs = Negotiation.objects.filter(user=user)
        s = self.request.query_params.get('status', '')
        if s:
            qs = qs.filter(status=s)
        return qs.select_related('user', 'listing').order_by('-created_at')


class NegotiationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = NegotiationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        neg = get_object_or_404(Negotiation, pk=self.kwargs['pk'])
        if not self.request.user.is_admin and neg.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        return neg


class CreateNegotiationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateNegotiationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            prop = Property.objects.get(slug=serializer.validated_data['property_slug'])
            neg = Negotiation.objects.create(
                listing=prop,
                user=request.user,
                initial_offer=serializer.validated_data['offer_amount'],
                current_offer=serializer.validated_data['offer_amount'],
                asking_price=prop.price,
            )
            NegotiationMessage.objects.create(
                negotiation=neg, sender=request.user,
                message_text=serializer.validated_data['message_text'],
                offer_amount=serializer.validated_data['offer_amount']
            )
            return Response(NegotiationDetailSerializer(neg, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RespondNegotiationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_admin:
            return Response({'error': 'Admin only.'}, status=status.HTTP_403_FORBIDDEN)
        neg = get_object_or_404(Negotiation, pk=pk)
        serializer = RespondNegotiationSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data['action']
            if action == 'accept':
                neg.status = 'accepted'
                neg.resolved_at = timezone.now()
            elif action == 'reject':
                neg.status = 'rejected'
                neg.resolved_at = timezone.now()
            elif action == 'counter':
                neg.status = 'counter_offered'
                neg.counter_offer = serializer.validated_data['counter_offer_amount']
            neg.handled_by = request.user
            neg.save()
            NegotiationMessage.objects.create(
                negotiation=neg, sender=request.user,
                message_text=serializer.validated_data['message_text'],
                offer_amount=serializer.validated_data.get('counter_offer_amount'),
                is_admin_reply=True
            )
            return Response(NegotiationDetailSerializer(neg, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
