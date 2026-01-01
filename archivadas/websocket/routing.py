# Archivadas/websocket/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/archivadas/$', consumers.ArchivadaConsumer.as_asgi()),
]
