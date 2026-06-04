"""ZB Lands and Home WSGI"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zb_lands_home.settings.base')
application = get_wsgi_application()
