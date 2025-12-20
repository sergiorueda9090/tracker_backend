# user/websocket/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


def get_timestamp():
    """Retorna timestamp ISO"""
    return datetime.now().isoformat()


def broadcast_user_connected(user_data):
    """
    Notifica a todos que un usuario se conectó
    
    Args:
        user_data (dict): Datos del usuario conectado
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'users_online',
        {
            'type': 'user_connected',
            'user': user_data,
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Usuario conectado - {user_data.get('name')}")


def broadcast_user_disconnected(user_data):
    """
    Notifica a todos que un usuario se desconectó
    
    Args:
        user_data (dict): Datos del usuario desconectado
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'users_online',
        {
            'type': 'user_disconnected',
            'user': user_data,
            'timestamp': get_timestamp()
        }
    )
    print(f"❌ WebSocket: Usuario desconectado - {user_data.get('name')}")


def get_connected_users():
    """
    Retorna la lista de usuarios conectados actualmente
    
    Returns:
        list: Lista de usuarios conectados
    """
    from .consumers import UsersOnlineConsumer
    
    unique_users = {}
    for channel_data in UsersOnlineConsumer.connected_users.values():
        user_id = channel_data['user_id']
        if user_id not in unique_users:
            unique_users[user_id] = channel_data['user_data']
    
    return list(unique_users.values())


def get_online_count():
    """
    Retorna el número de usuarios conectados
    
    Returns:
        int: Cantidad de usuarios en línea
    """
    from .consumers import UsersOnlineConsumer
    return UsersOnlineConsumer.get_online_count()


def is_user_online(user_id):
    """
    Verifica si un usuario específico está en línea
    
    Args:
        user_id (int): ID del usuario
        
    Returns:
        bool: True si está en línea, False si no
    """
    from .consumers import UsersOnlineConsumer
    return UsersOnlineConsumer.is_user_online(user_id)