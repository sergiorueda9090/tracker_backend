# preparacion/websocket/routing.py
from django.urls import re_path
from .consumers import PreparacionConsumer

websocket_urlpatterns = [
    re_path(r'ws/preparacion/$', PreparacionConsumer.as_asgi()),
]