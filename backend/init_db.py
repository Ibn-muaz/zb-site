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

if __name__ == '__main__':
    run()
