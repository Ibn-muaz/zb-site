"""Content app views - home, about, contact, FAQ, blog"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.core.mail import send_mail
from django.conf import settings
from .models import SiteSettings, Banner, Testimonial, FAQ, BlogPost, ContactInquiry
from apps.properties.models import Property
from rest_framework.views import APIView
from rest_framework.response import Response


class HomeView(TemplateView):
    template_name = 'home/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['featured_properties'] = Property.objects.filter(
            is_featured=True, is_active=True, status='available'
        ).prefetch_related('images')[:6]
        ctx['recent_properties'] = Property.objects.filter(
            is_active=True, status='available'
        ).prefetch_related('images').order_by('-created_at')[:8]
        ctx['testimonials'] = Testimonial.objects.filter(is_active=True)[:6]
        ctx['banners'] = Banner.objects.filter(is_active=True)
        ctx['blog_posts'] = BlogPost.objects.filter(is_published=True)[:3]
        ctx['total_properties'] = Property.objects.filter(is_active=True).count()
        ctx['total_sold'] = Property.objects.filter(status='sold').count()
        ctx['total_rented'] = Property.objects.filter(status='rented').count()
        return ctx


class AboutView(TemplateView):
    template_name = 'content/about.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['testimonials'] = Testimonial.objects.filter(is_active=True)[:4]
        ctx['total_properties'] = Property.objects.filter(is_active=True).count()
        ctx['total_sold'] = Property.objects.filter(status='sold').count()
        return ctx


class ContactView(View):
    template_name = 'content/contact.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and subject and message:
            inquiry = ContactInquiry.objects.create(
                name=name, email=email, phone=phone,
                subject=subject, message=message
            )
            try:
                send_mail(
                    f'[ZB Lands and Home] New Inquiry: {subject}',
                    f'From: {name} <{email}>\nPhone: {phone}\n\n{message}',
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.EMAIL_HOST_USER or 'admin@ZBLandsAndHome.com'],
                    fail_silently=True,
                )
            except Exception:
                pass
            messages.success(request, 'Your message has been sent! We will get back to you soon.')
            return redirect('contact')
        else:
            messages.error(request, 'Please fill in all required fields.')
        return render(request, self.template_name)


class FAQView(TemplateView):
    template_name = 'content/faq.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['faqs'] = FAQ.objects.filter(is_active=True)
        categories = FAQ.objects.filter(is_active=True).values_list('category', flat=True).distinct()
        ctx['categories'] = [c for c in categories if c]
        return ctx


class BlogListView(ListView):
    model = BlogPost
    template_name = 'content/blog_list.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related('author')


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'content/blog_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'

    def get_object(self, **kwargs):
        obj = super().get_object(**kwargs)
        obj.view_count += 1
        obj.save(update_fields=['view_count'])
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['related_posts'] = BlogPost.objects.filter(
            is_published=True
        ).exclude(pk=self.object.pk)[:3]
        return ctx


class SiteSettingsAPIView(APIView):
    def get(self, request):
        site = SiteSettings.get_settings()
        return Response({
            'company_name': site.company_name,
            'company_email': site.company_email,
            'company_phone': site.company_phone,
            'company_address': site.company_address,
        })
