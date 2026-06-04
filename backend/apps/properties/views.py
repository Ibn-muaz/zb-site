"""Properties app views"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from rest_framework import generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from .models import Property, PropertyImage, PropertyView, SavedProperty, Amenity
from .serializers import PropertyListSerializer, PropertyDetailSerializer, PropertyCreateSerializer, PropertyImageSerializer
from .filters import PropertyFilter


# ──────────────────────── WEB VIEWS ────────────────────────

class PropertyListView(TemplateView):
    template_name = 'properties/list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Property.objects.filter(is_active=True).prefetch_related('images').select_related('admin')
        f = PropertyFilter(self.request.GET, queryset=qs)
        paginator = Paginator(f.qs, 12)
        page = paginator.get_page(self.request.GET.get('page', 1))
        ctx['properties'] = page
        ctx['paginator'] = paginator
        ctx['filter'] = f
        ctx['total_count'] = f.qs.count()
        ctx['states'] = Property.objects.filter(is_active=True).values_list('state', flat=True).distinct().order_by('state')
        ctx['cities'] = Property.objects.filter(is_active=True).values_list('city', flat=True).distinct().order_by('city')
        ctx['amenities'] = Amenity.objects.all()
        return ctx


class PropertyDetailView(View):
    template_name = 'properties/detail.html'

    def get(self, request, slug):
        prop = get_object_or_404(Property, slug=slug, is_active=True)
        # Track view
        prop.view_count += 1
        prop.save(update_fields=['view_count'])
        PropertyView.objects.create(
            property=prop,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        is_saved = False
        existing_negotiation = None
        if request.user.is_authenticated:
            is_saved = SavedProperty.objects.filter(user=request.user, property=prop).exists()
            from apps.negotiations.models import Negotiation
            existing_negotiation = Negotiation.objects.filter(
                user=request.user, property=prop, status__in=['pending', 'counter_offered']
            ).first()

        related = Property.objects.filter(
            is_active=True, city=prop.city
        ).exclude(pk=prop.pk).prefetch_related('images')[:4]
        if related.count() < 4:
            related = Property.objects.filter(
                is_active=True, property_type=prop.property_type
            ).exclude(pk=prop.pk).prefetch_related('images')[:4]

        ctx = {
            'property': prop,
            'related_properties': related,
            'is_saved': is_saved,
            'existing_negotiation': existing_negotiation,
        }
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name='dispatch')
class SavePropertyView(View):
    def post(self, request, slug):
        prop = get_object_or_404(Property, slug=slug)
        saved, created = SavedProperty.objects.get_or_create(user=request.user, property=prop)
        if not created:
            saved.delete()
            return JsonResponse({'saved': False, 'message': 'Property removed from saved list.'})
        return JsonResponse({'saved': True, 'message': 'Property saved successfully!'})


class ComparePropertiesView(TemplateView):
    template_name = 'properties/compare.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ids = self.request.GET.getlist('ids')[:3]
        ctx['properties'] = Property.objects.filter(slug__in=ids, is_active=True).prefetch_related('images', 'amenities')
        return ctx


# ──────────────────────── ADMIN PROPERTY VIEWS ────────────────────────

def admin_required_redirect(request):
    return not request.user.is_authenticated or not request.user.is_admin


@method_decorator(login_required, name='dispatch')
class AdminPropertyListView(TemplateView):
    template_name = 'admin_panel/properties.html'

    def dispatch(self, request, *args, **kwargs):
        if admin_required_redirect(request):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '')
        status_f = self.request.GET.get('status', '')
        qs = Property.objects.prefetch_related('images')
        if q:
            qs = qs.filter(title__icontains=q)
        if status_f:
            qs = qs.filter(status=status_f)
        ctx['properties'] = qs.order_by('-created_at')
        ctx['q'] = q
        ctx['status_filter'] = status_f
        ctx['amenities'] = Amenity.objects.all()
        return ctx


@method_decorator(login_required, name='dispatch')
class AdminPropertyCreateView(View):
    template_name = 'admin_panel/property_form.html'

    def dispatch(self, request, *args, **kwargs):
        if admin_required_redirect(request):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {'amenities': Amenity.objects.all(), 'action': 'Add'})

    def post(self, request):
        data = request.POST.dict()
        amenity_ids = request.POST.getlist('amenities')
        data.pop('csrfmiddlewaretoken', None)
        data.pop('amenities', None)
        data['price_negotiable'] = 'price_negotiable' in request.POST
        data['is_featured'] = 'is_featured' in request.POST
        data['is_active'] = 'is_active' in request.POST

        try:
            prop = Property(admin=request.user)
            for k, v in data.items():
                if hasattr(prop, k) and v:
                    setattr(prop, k, v)
            prop.save()
            if amenity_ids:
                prop.amenities.set(Amenity.objects.filter(id__in=amenity_ids))
            # Handle images
            for img in request.FILES.getlist('images'):
                pi = PropertyImage.objects.create(property=prop, image=img)
                if not PropertyImage.objects.filter(property=prop, is_primary=True).exclude(pk=pi.pk).exists():
                    pi.is_primary = True
                    pi.save()
            messages.success(request, f'Property "{prop.title}" created successfully.')
            return redirect('admin-properties')
        except Exception as e:
            messages.error(request, f'Error creating property: {e}')
        return render(request, self.template_name, {'amenities': Amenity.objects.all(), 'action': 'Add'})


@method_decorator(login_required, name='dispatch')
class AdminPropertyEditView(View):
    template_name = 'admin_panel/property_form.html'

    def dispatch(self, request, *args, **kwargs):
        if admin_required_redirect(request):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, slug):
        prop = get_object_or_404(Property, slug=slug)
        return render(request, self.template_name, {
            'property': prop, 'amenities': Amenity.objects.all(), 'action': 'Edit'
        })

    def post(self, request, slug):
        prop = get_object_or_404(Property, slug=slug)
        data = request.POST.dict()
        amenity_ids = request.POST.getlist('amenities')
        data.pop('csrfmiddlewaretoken', None)
        data.pop('amenities', None)
        data['price_negotiable'] = 'price_negotiable' in request.POST
        data['is_featured'] = 'is_featured' in request.POST
        data['is_active'] = 'is_active' in request.POST
        try:
            for k, v in data.items():
                if hasattr(prop, k) and k not in ['slug', 'id']:
                    setattr(prop, k, v)
            prop.save()
            prop.amenities.set(Amenity.objects.filter(id__in=amenity_ids))
            for img in request.FILES.getlist('images'):
                PropertyImage.objects.create(property=prop, image=img)
            messages.success(request, f'Property "{prop.title}" updated.')
            return redirect('admin-properties')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return render(request, self.template_name, {
            'property': prop, 'amenities': Amenity.objects.all(), 'action': 'Edit'
        })


@method_decorator(login_required, name='dispatch')
class AdminPropertyDeleteView(View):
    def dispatch(self, request, *args, **kwargs):
        if admin_required_redirect(request):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, slug):
        prop = get_object_or_404(Property, slug=slug)
        title = prop.title
        prop.delete()
        messages.success(request, f'Property "{title}" deleted.')
        return redirect('admin-properties')


# ──────────────────────── REST API VIEWS ────────────────────────

class PropertyListAPIView(generics.ListAPIView):
    queryset = Property.objects.filter(is_active=True).prefetch_related('images', 'amenities')
    serializer_class = PropertyListSerializer
    filterset_class = PropertyFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'city', 'state', 'description']
    ordering_fields = ['price', 'created_at', 'view_count', 'bedrooms']
    ordering = ['-created_at']


class PropertyDetailAPIView(generics.RetrieveAPIView):
    queryset = Property.objects.filter(is_active=True).prefetch_related('images', 'amenities')
    serializer_class = PropertyDetailSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.view_count += 1
        instance.save(update_fields=['view_count'])
        return super().retrieve(request, *args, **kwargs)


class FeaturedPropertiesAPIView(generics.ListAPIView):
    queryset = Property.objects.filter(is_featured=True, is_active=True, status='available').prefetch_related('images')
    serializer_class = PropertyListSerializer


class SavePropertyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        prop = get_object_or_404(Property, slug=slug)
        saved, created = SavedProperty.objects.get_or_create(user=request.user, property=prop)
        if not created:
            saved.delete()
            return Response({'saved': False})
        return Response({'saved': True})


class PropertySearchAPIView(generics.ListAPIView):
    serializer_class = PropertyListSerializer

    def get_queryset(self):
        q = self.request.query_params.get('q', '')
        from django.db.models import Q
        return Property.objects.filter(
            is_active=True
        ).filter(
            Q(title__icontains=q) | Q(city__icontains=q) |
            Q(state__icontains=q) | Q(description__icontains=q)
        ).prefetch_related('images')[:20]
