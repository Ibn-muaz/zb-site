"""Notifications views and helpers"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification


def create_notification(user, notification_type, title, message, link=''):
    """Helper function to create a notification for a user."""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


class NotificationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base_qs = Notification.objects.filter(user=request.user)
        unread_count = base_qs.filter(is_read=False).count()
        notifications = base_qs[:20]
        data = [{
            'id': str(n.id),
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'link': n.link,
            'created_at': n.created_at.isoformat(),
        } for n in notifications]
        return Response({'notifications': data, 'unread_count': unread_count})


class MarkNotificationReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if pk:
            Notification.objects.filter(user=request.user, id=pk).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


class NotificationListView(ListView):
    template_name = 'accounts/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
