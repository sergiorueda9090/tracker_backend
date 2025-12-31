# preparacion/websocket/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class PreparacionConsumer(AsyncWebsocketConsumer):
    """
    Consumer para manejar conexiones WebSocket de la aplicación Preparación.
    Gestiona actualizaciones en tiempo real de trámites de preparación.
    """
    
    async def connect(self):
        """
            Se ejecuta cuando un cliente se conecta al WebSocket
        """
        # Nombre del grupo para actualizaciones de preparación
        self.room_group_name = 'preparacion_updates'

        # Usuario (si está autenticado)
        self.user = self.scope.get('user')

        # Únete al grupo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Acepta la conexión
        await self.accept()

        # Envía mensaje de bienvenida
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado a actualizaciones de Preparación en tiempo real',
            'timestamp': self.get_timestamp()
        }))

    async def disconnect(self, close_code):
        """
        Se ejecuta cuando un cliente se desconecta
        """
        # Sale del grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        print(f"Cliente desconectado del grupo {self.room_group_name}")

    async def receive(self, text_data):
        """
        Recibe mensajes del WebSocket desde el cliente
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            # Manejar diferentes tipos de mensajes
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'pong',
                    'timestamp': self.get_timestamp()
                }))
            
            elif message_type == 'subscribe':
                # Suscribirse a un trámite específico
                preparacion_id = text_data_json.get('preparacion_id')
                if preparacion_id:
                    await self.subscribe_to_preparacion(preparacion_id)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Formato de mensaje inválido',
                'timestamp': self.get_timestamp()
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e),
                'timestamp': self.get_timestamp()
            }))

    # ===== Event Handlers =====
    async def preparacion_created(self, event):
        """
        Envía notificación cuando se crea una preparación
        """
        await self.send(text_data=json.dumps({
            'type': 'preparacion_created',
            'data': event['data'],
            'message': 'Nueva preparación creada',
            'timestamp': self.get_timestamp()
        }))

    async def preparacion_updated(self, event):
        """
        Envía notificación cuando se actualiza una preparación
        """
        await self.send(text_data=json.dumps({
            'type': 'preparacion_updated',
            'data': event['data'],
            'message': 'Preparación actualizada',
            'timestamp': self.get_timestamp()
        }))

    async def preparacion_deleted(self, event):
        """
        Envía notificación cuando se elimina una preparación
        """
        await self.send(text_data=json.dumps({
            'type': 'preparacion_deleted',
            'data': event['data'],
            'message': 'Preparación eliminada',
            'timestamp': self.get_timestamp()
        }))

    async def preparacion_status_changed(self, event):
        """
        Envía notificación cuando cambia el estado de una preparación
        """
        await self.send(text_data=json.dumps({
            'type': 'preparacion_status_changed',
            'data': event['data'],
            'message': f"Estado cambiado a: {event['data'].get('status')}",
            'timestamp': self.get_timestamp()
        }))

    async def archivo_deleted(self, event):
        """
        Envía notificación cuando se elimina un archivo de un trámite
        """
        await self.send(text_data=json.dumps({
            'type': 'archivo_deleted',
            'data': event['data'],
            'message': f"Archivo eliminado: {event['data'].get('nombre_archivo')}",
            'timestamp': self.get_timestamp()
        }))

    # ===== Helper Methods =====
    async def subscribe_to_preparacion(self, preparacion_id):
        """
        Suscribe al usuario a actualizaciones de un trámite específico
        """
        specific_group = f'preparacion_{preparacion_id}'
        await self.channel_layer.group_add(
            specific_group,
            self.channel_name
        )
        
        await self.send(text_data=json.dumps({
            'type': 'subscribed',
            'preparacion_id': preparacion_id,
            'message': f'Suscrito a actualizaciones del trámite {preparacion_id}',
            'timestamp': self.get_timestamp()
        }))

    @staticmethod
    def get_timestamp():
        """
        Retorna el timestamp actual en formato ISO
        """
        from datetime import datetime
        return datetime.now().isoformat()