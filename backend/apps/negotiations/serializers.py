"""Negotiations serializers"""
from rest_framework import serializers
from .models import Negotiation, NegotiationMessage
from apps.accounts.serializers import UserMiniSerializer


class NegotiationMessageSerializer(serializers.ModelSerializer):
    sender = UserMiniSerializer(read_only=True)

    class Meta:
        model = NegotiationMessage
        fields = ['id', 'sender', 'message_text', 'offer_amount', 'is_admin_reply', 'is_read', 'timestamp']


class NegotiationListSerializer(serializers.ModelSerializer):
    user = UserMiniSerializer(read_only=True)
    property_title = serializers.CharField(source='listing.title', read_only=True)
    property_slug = serializers.CharField(source='listing.slug', read_only=True)
    property_image = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Negotiation
        fields = [
            'id', 'property_title', 'property_slug', 'property_image',
            'user', 'initial_offer', 'current_offer', 'counter_offer',
            'asking_price', 'status', 'status_display', 'created_at', 'unread_count',
        ]

    def get_property_image(self, obj):
        request = self.context.get('request')
        img = obj.listing.images.filter(is_primary=True).first() or obj.listing.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0


class NegotiationDetailSerializer(NegotiationListSerializer):
    messages = NegotiationMessageSerializer(many=True, read_only=True)
    admin = UserMiniSerializer(read_only=True)

    class Meta(NegotiationListSerializer.Meta):
        fields = NegotiationListSerializer.Meta.fields + ['messages', 'admin', 'notes', 'updated_at', 'resolved_at']


class CreateNegotiationSerializer(serializers.Serializer):
    property_slug = serializers.SlugField()
    offer_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    message_text = serializers.CharField()

    def validate_property_slug(self, value):
        from apps.properties.models import Property
        try:
            prop = Property.objects.get(slug=value, is_active=True)
            if prop.status != 'available':
                raise serializers.ValidationError('This property is not available for negotiation.')
            return value
        except Property.DoesNotExist:
            raise serializers.ValidationError('Property not found.')

    def validate(self, attrs):
        request = self.context.get('request')
        from apps.properties.models import Property
        prop = Property.objects.get(slug=attrs['property_slug'])
        if Negotiation.objects.filter(
            user=request.user, property=prop, status__in=['pending', 'counter_offered']
        ).exists():
            raise serializers.ValidationError('You already have an active negotiation for this property.')
        if attrs['offer_amount'] <= 0:
            raise serializers.ValidationError({'offer_amount': 'Offer must be greater than 0.'})
        return attrs


class RespondNegotiationSerializer(serializers.Serializer):
    ACTION_CHOICES = ['accept', 'reject', 'counter']
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    counter_offer_amount = serializers.DecimalField(max_digits=15, decimal_places=2, required=False, allow_null=True)
    message_text = serializers.CharField()

    def validate(self, attrs):
        if attrs['action'] == 'counter' and not attrs.get('counter_offer_amount'):
            raise serializers.ValidationError({'counter_offer_amount': 'Counter offer amount required.'})
        return attrs
