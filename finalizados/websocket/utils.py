# finalizado/websocket/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def notify_finalizado_created(finalizado_data):
    """
    Notifica a todos los clientes conectados que se creó un nuevo trámite en finalizado.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "finalizado_updates",
        {
            "type": "finalizado_created",
            "data": finalizado_data
        }
    )


def notify_finalizado_updated(finalizado_data):
    """
    Notifica a todos los clientes conectados que se actualizó un trámite en finalizado.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "finalizado_updates",
        {
            "type": "finalizado_updated",
            "data": finalizado_data
        }
    )


def notify_finalizado_deleted(finalizado_id, finalizado_placa):
    """
    Notifica a todos los clientes conectados que se eliminó un trámite en finalizado.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "finalizado_updates",
        {
            "type": "finalizado_deleted",
            "data": {
                "id": finalizado_id,
                "placa": finalizado_placa
            }
        }
    )
