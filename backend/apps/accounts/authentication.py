import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def get_neon_jwks_client():
    jwks_url = settings.NEON_AUTH_JWKS_URL
    if not jwks_url:
        raise ValueError("NEON_AUTH_JWKS_URL is not set in settings")
    return PyJWKClient(jwks_url)

def decode_neon_token(token):
    try:
        jwks_client = get_neon_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return data
    except jwt.PyJWTError as e:
        logger.error(f"JWT decode error: {e}")
        return None

def get_or_create_user_from_token(payload):
    user_id = payload.get('sub')
    email = payload.get('email', '')
    
    if not user_id:
        return None
        
    try:
        if not email:
            email = f"{user_id}@neon-auth.local"
            
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0] + '_' + user_id[:5],
                'is_active': True,
                # Give them admin privileges for testing if they log in via Neon Auth,
                # or handle roles appropriately in production.
                'role': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        # If user already exists but isn't staff (for admin access), update them for this demo
        if not created and not user.is_staff:
            user.is_staff = True
            user.is_superuser = True
            user.role = 'super_admin'
            user.save()
            
        return user
    except Exception as e:
        logger.error(f"User mapping error: {e}")
        return None

class NeonJWTAuthentication(BaseAuthentication):
    """
    DRF Authentication Class for verifying Neon Auth tokens.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        payload = decode_neon_token(token)
        
        if not payload:
            raise AuthenticationFailed('Invalid or expired Neon Auth token')
            
        user = get_or_create_user_from_token(payload)
        if not user:
            raise AuthenticationFailed('User could not be mapped')
            
        return (user, token)

from django.contrib.auth.backends import BaseBackend

class NeonDjangoBackend(BaseBackend):
    """
    Django Authentication Backend to authenticate using a Neon Auth token directly.
    """
    def authenticate(self, request, token=None, **kwargs):
        if not token:
            return None
            
        payload = decode_neon_token(token)
        if payload:
            user = get_or_create_user_from_token(payload)
            return user
        return None
        
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
