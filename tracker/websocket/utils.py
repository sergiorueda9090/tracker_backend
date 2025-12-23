# tracker/websocket/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def notify_tracker_created(tracker_data):
    """
    Notifica a todos los clientes conectados que se creó un nuevo trámite en Tracker.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tracker_updates",
        {
            "type": "tracker_created",
            "data": tracker_data
        }
    )


def notify_tracker_updated(tracker_data):
    """
    Notifica a todos los clientes conectados que se actualizó un trámite en Tracker.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tracker_updates",
        {
            "type": "tracker_updated",
            "data": tracker_data
        }
    )


def notify_tracker_deleted(tracker_id, tracker_placa):
    """
    Notifica a todos los clientes conectados que se eliminó un trámite en Tracker.
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "tracker_updates",
        {
            "type": "tracker_deleted",
            "data": {
                "id": tracker_id,
                "placa": tracker_placa
            }
        }
    )
