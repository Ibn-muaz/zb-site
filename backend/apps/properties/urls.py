"""Properties URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.PropertyListView.as_view(), name='property-list'),
    path('compare/', views.ComparePropertiesView.as_view(), name='compare-properties'),
    path('<slug:slug>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('<slug:slug>/save/', views.SavePropertyView.as_view(), name='save-property'),
]
