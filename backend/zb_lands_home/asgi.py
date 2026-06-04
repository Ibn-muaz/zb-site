"""ZB Lands and Home ASGI"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zb_lands_home.settings.base')
application = get_asgi_application()
