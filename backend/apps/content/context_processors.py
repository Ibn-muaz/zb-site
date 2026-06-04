"""Content app context processors"""
from .models import SiteSettings


def site_settings(request):
    """Make site settings available in all templates"""
    return {'site': SiteSettings.get_settings()}
