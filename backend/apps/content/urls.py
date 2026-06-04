"""Content app URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('blog/', views.BlogListView.as_view(), name='blog-list'),
    path('blog/<slug:slug>/', views.BlogDetailView.as_view(), name='blog-detail'),
]
