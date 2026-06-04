"""Negotiations URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.NegotiationListView.as_view(), name='negotiation-list'),
    path('<uuid:pk>/', views.NegotiationDetailView.as_view(), name='negotiation-detail'),
    path('create/<slug:property_slug>/', views.CreateNegotiationView.as_view(), name='create-negotiation'),
]
