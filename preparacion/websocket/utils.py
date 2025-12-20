# preparacion/websocket/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


def get_timestamp():
    """Retorna timestamp ISO"""
    return datetime.now().isoformat()


def notify_preparacion_created(preparacion_data):
    """
    Notifica a todos los clientes conectados que se creó una preparación
    
    Args:
        preparacion_data (dict): Datos serializados de la preparación
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'preparacion_updates',
        {
            'type': 'preparacion_created',
            'data': preparacion_data,
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Notificación de creación enviada - ID: {preparacion_data.get('id')}")


def notify_preparacion_updated(preparacion_data):
    """
    Notifica a todos los clientes conectados que se actualizó una preparación
    
    Args:
        preparacion_data (dict): Datos serializados de la preparación
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'preparacion_updates',
        {
            'type': 'preparacion_updated',
            'data': preparacion_data,
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Notificación de actualización enviada - ID: {preparacion_data.get('id')}")


def notify_preparacion_deleted(preparacion_id):
    """
    Notifica a todos los clientes conectados que se eliminó una preparación
    
    Args:
        preparacion_id (int): ID de la preparación eliminada
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'preparacion_updates',
        {
            'type': 'preparacion_deleted',
            'data': {'id': preparacion_id},
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Notificación de eliminación enviada - ID: {preparacion_id}")


def notify_preparacion_status_changed(preparacion_data):
    """
    Notifica cuando cambia el estado de una preparación
    
    Args:
        preparacion_data (dict): Datos con el nuevo estado
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'preparacion_updates',
        {
            'type': 'preparacion_status_changed',
            'data': preparacion_data,
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Notificación de cambio de estado - ID: {preparacion_data.get('id')}")


def notify_specific_preparacion(preparacion_id, event_type, data):
    """
    Notifica solo a los usuarios suscritos a un trámite específico
    
    Args:
        preparacion_id (int): ID del trámite
        event_type (str): Tipo de evento
        data (dict): Datos del evento
    """
    channel_layer = get_channel_layer()
    group_name = f'preparacion_{preparacion_id}'
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': event_type,
            'data': data,
            'timestamp': get_timestamp()
        }
    )
    print(f"✅ WebSocket: Notificación específica enviada - Grupo: {group_name}")