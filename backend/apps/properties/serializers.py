"""Properties app serializers"""
from rest_framework import serializers
from .models import Property, PropertyImage, Amenity, SavedProperty
from apps.accounts.serializers import UserMiniSerializer


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'icon']


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'image_url', 'caption', 'is_primary', 'order']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class PropertyListSerializer(serializers.ModelSerializer):
    main_image_url = serializers.SerializerMethodField()
    formatted_price = serializers.CharField(read_only=True)
    is_saved = serializers.SerializerMethodField()
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    listing_type_display = serializers.CharField(source='get_listing_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'title', 'slug', 'property_type', 'property_type_display',
            'listing_type', 'listing_type_display', 'status', 'status_display',
            'city', 'state', 'price', 'formatted_price', 'bedrooms', 'bathrooms',
            'parking_spaces', 'area_sqft', 'is_featured', 'main_image_url',
            'is_saved', 'created_at',
        ]

    def get_main_image_url(self, obj):
        request = self.context.get('request')
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedProperty.objects.filter(user=request.user, property=obj).exists()
        return False


class PropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    admin = UserMiniSerializer(read_only=True)
    formatted_price = serializers.CharField(read_only=True)
    is_saved = serializers.SerializerMethodField()
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    listing_type_display = serializers.CharField(source='get_listing_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Property
        fields = '__all__'

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedProperty.objects.filter(user=request.user, property=obj).exists()
        return False


class PropertyCreateSerializer(serializers.ModelSerializer):
    amenity_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Property
        exclude = ['admin', 'view_count', 'created_at', 'updated_at', 'slug']

    def create(self, validated_data):
        amenity_ids = validated_data.pop('amenity_ids', [])
        request = self.context['request']
        prop = Property.objects.create(admin=request.user, **validated_data)
        if amenity_ids:
            prop.amenities.set(Amenity.objects.filter(id__in=amenity_ids))
        return prop

    def update(self, instance, validated_data):
        amenity_ids = validated_data.pop('amenity_ids', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if amenity_ids is not None:
            instance.amenities.set(Amenity.objects.filter(id__in=amenity_ids))
        return instance
