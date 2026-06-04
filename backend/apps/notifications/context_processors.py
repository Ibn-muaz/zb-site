"""Notifications context processor"""
from .models import Notification


def notifications(request):
    """Inject unread notification count into all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
        return {'unread_notifications': unread_count, 'recent_notifications': recent}
    return {'unread_notifications': 0, 'recent_notifications': []}
