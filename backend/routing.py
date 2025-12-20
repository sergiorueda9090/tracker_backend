# backend/routing.py
from django.urls import re_path
from . import consumers

# Importa los routings de cada aplicación
from preparacion.websocket.routing import websocket_urlpatterns as preparacion_ws_urls
from user.websocket.routing import websocket_urlpatterns as user_ws_urls
# from user.websocket.routing import websocket_urlpatterns as user_ws_urls  # Futuro

# Combina todas las rutas WebSocket
websocket_urlpatterns = [
    # Ruta de prueba (puedes mantenerla o eliminarla después)
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
    
    # Rutas de las aplicaciones
] + preparacion_ws_urls + user_ws_urls # + user_ws_urls (cuando lo crees)

print("📡 WebSocket routes registered:")
for pattern in websocket_urlpatterns:
    print(f"  - {pattern.pattern}")