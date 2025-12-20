import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Únete a un grupo de prueba
        await self.channel_layer.group_add(
            "test_group",
            self.channel_name
        )
        await self.accept()
        
        # Envía mensaje de bienvenida
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': '¡Conexión WebSocket establecida con éxito!'
        }))

    async def disconnect(self, close_code):
        # Sal del grupo
        await self.channel_layer.group_discard(
            "test_group",
            self.channel_name
        )

    async def receive(self, text_data):
        """Recibe mensajes del WebSocket"""
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        # Envía el mensaje a todos en el grupo
        await self.channel_layer.group_send(
            "test_group",
            {
                'type': 'test_message',
                'message': message
            }
        )

    async def test_message(self, event):
        """Envía el mensaje al WebSocket"""
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message,
            'echo': f'Echo: {message}'
        }))