# tracker/websocket/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TrackerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer para actualizaciones en tiempo real del módulo Tracker.

    Maneja conexiones WebSocket y distribuye notificaciones de eventos:
    - Trámite creado
    - Trámite actualizado
    - Trámite eliminado
    """

    async def connect(self):
        """Conecta al cliente y lo añade al grupo de actualizaciones"""
        # Unirse al grupo de actualizaciones de tracker
        await self.channel_layer.group_add(
            "tracker_updates",
            self.channel_name
        )

        await self.accept()

        # Enviar mensaje de confirmación de conexión
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': '✅ Conectado a actualizaciones de Tracker en tiempo real'
        }))

    async def disconnect(self, close_code):
        """Desconecta al cliente del grupo de actualizaciones"""
        await self.channel_layer.group_discard(
            "tracker_updates",
            self.channel_name
        )

    async def receive(self, text_data):
        """Maneja mensajes recibidos del cliente"""
        try:
            data = json.loads(text_data)
            # Aquí puedes manejar mensajes del cliente si es necesario
            print(f"📩 Mensaje recibido del cliente: {data}")
        except json.JSONDecodeError:
            print("⚠️ Error al decodificar JSON del cliente")

    # Handlers para eventos del grupo
    async def tracker_created(self, event):
        """Envía notificación de trámite creado"""
        await self.send(text_data=json.dumps({
            'type': 'tracker_created',
            'data': event['data']
        }))

    async def tracker_updated(self, event):
        """Envía notificación de trámite actualizado"""
        await self.send(text_data=json.dumps({
            'type': 'tracker_updated',
            'data': event['data']
        }))

    async def tracker_deleted(self, event):
        """Envía notificación de trámite eliminado"""
        await self.send(text_data=json.dumps({
            'type': 'tracker_deleted',
            'data': event['data']
        }))
