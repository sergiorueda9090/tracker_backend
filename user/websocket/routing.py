# user/websocket/routing.py
from django.urls import re_path
from .consumers import UsersOnlineConsumer

websocket_urlpatterns = [
    re_path(r'ws/users/online/$', UsersOnlineConsumer.as_asgi()),
]