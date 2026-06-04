"""Negotiations signals"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Negotiation, NegotiationMessage


@receiver(post_save, sender=Negotiation)
def negotiation_status_notify(sender, instance, created, **kwargs):
    from apps.notifications.views import create_notification
    from apps.accounts.models import CustomUser

    if created:
        # Notify all admins
        admins = CustomUser.objects.filter(role__in=['admin', 'super_admin'])
        for admin in admins:
            create_notification(
                user=admin,
                notification_type='new_offer',
                title='New Offer Received',
                message=f'{instance.user.full_name} made an offer of ₦{instance.initial_offer:,.0f} on "{instance.listing.title}"',
                link=f'/admin-panel/negotiations/{instance.pk}/',
            )
    else:
        # Notify user of status change
        status_messages = {
            'accepted': ('offer_accepted', 'Offer Accepted! 🎉', f'Your offer on "{instance.listing.title}" has been accepted.'),
            'rejected': ('offer_rejected', 'Offer Rejected', f'Your offer on "{instance.listing.title}" was not accepted.'),
            'counter_offered': ('counter_offer', 'Counter Offer Received', f'Admin has made a counter offer of ₦{instance.counter_offer:,.0f} on "{instance.listing.title}"'),
        }
        if instance.status in status_messages:
            ntype, title, msg = status_messages[instance.status]
            create_notification(
                user=instance.user,
                notification_type=ntype,
                title=title,
                message=msg,
                link=f'/negotiations/{instance.pk}/',
            )


@receiver(post_save, sender=NegotiationMessage)
def message_notify(sender, instance, created, **kwargs):
    if not created:
        return
    from apps.notifications.views import create_notification
    negotiation = instance.negotiation
    # Notify the other party
    if instance.is_admin_reply:
        recipient = negotiation.user
        create_notification(
            user=recipient,
            notification_type='new_message',
            title='New Reply on Your Negotiation',
            message=f'Admin replied to your negotiation on "{negotiation.listing.title}"',
            link=f'/negotiations/{negotiation.pk}/',
        )
    else:
        from apps.accounts.models import CustomUser
        admins = CustomUser.objects.filter(role__in=['admin', 'super_admin'])
        for admin in admins:
            create_notification(
                user=admin,
                notification_type='new_message',
                title='New Message in Negotiation',
                message=f'{instance.sender.full_name} sent a message on "{negotiation.listing.title}"',
                link=f'/admin-panel/negotiations/{negotiation.pk}/',
            )
