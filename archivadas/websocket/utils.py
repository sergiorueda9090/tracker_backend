# archivada/websocket/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def notify_archivada_created(archivada_data):
    """
    Notifica a todos los clientes conectados que se creó un nuevo trámite en archivada.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "archivada_updates",
        {
            "type": "archivada_created",
            "data": archivada_data
        }
    )


def notify_archivada_updated(archivada_data):
    """
    Notifica a todos los clientes conectados que se actualizó un trámite en archivada.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "archivada_updates",
        {
            "type": "archivada_updated",
            "data": archivada_data
        }
    )


def notify_archivada_deleted(archivada_id, archivada_placa):
    """
    Notifica a todos los clientes conectados que se eliminó un trámite en archivada.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "archivada_updates",
        {
            "type": "archivada_deleted",
            "data": {
                "id": archivada_id,
                "placa": archivada_placa
            }
        }
    )
