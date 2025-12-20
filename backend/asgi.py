# backend/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Inicializa Django ASGI application PRIMERO
django_asgi_app = get_asgi_application()

# Ahora importa channels y routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from backend import routing
from backend.middleware import JWTAuthMiddlewareStack  # ← Importar nuestro middleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(  # ← Usar nuestro middleware JWT
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})