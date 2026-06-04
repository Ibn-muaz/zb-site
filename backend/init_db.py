import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zb_lands_home.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from apps.properties.models import Property

User = get_user_model()

def run():
    # 1. Create Superuser
    if not User.objects.filter(email='admin@ZBLandsAndHome.com').exists():
        admin = User.objects.create_superuser(
            email='admin@ZBLandsAndHome.com',
            username='admin',
            password='adminpassword123',
            first_name='ZB',
            last_name='Admin',
            role='super_admin',
            is_verified=True
        )
        print("✅ Superuser created: admin@ZBLandsAndHome.com / adminpassword123")
    else:
        admin = User.objects.get(email='admin@ZBLandsAndHome.com')
        print("✅ Superuser already exists.")

    # 2. Create a Dummy Property
    if not Property.objects.exists():
        Property.objects.create(
            title="Luxury 5-Bedroom Detached Duplex in Ikoyi",
            description="Exquisitely finished 5-bedroom fully detached duplex with a swimming pool, smart home automation, and a BQ in the prestigious heart of Ikoyi, Lagos. Ideal for high net-worth individuals seeking premium comfort and security.",
            property_type='duplex',
            listing_type='sale',
            status='available',
            price=450000000.00,
            address="12 Bourdillon Road",
            city="Ikoyi",
            state="Lagos",
            country="Nigeria",
            bedrooms=5,
            bathrooms=6,
            parking_spaces=4,
            area_sqft=4500,
            is_featured=True,
            price_negotiable=True,
            admin=admin
        )
        print("✅ Dummy property created.")

if __name__ == '__main__':
    run()
