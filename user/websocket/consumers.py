# user/websocket/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class UsersOnlineConsumer(AsyncWebsocketConsumer):
    """Consumer para manejar usuarios conectados en tiempo real."""
    
    connected_users = {}
    
    async def connect(self):
        """Se ejecuta cuando un cliente se conecta al WebSocket"""
        print("=" * 50)
        print("🔵 [UsersOnlineConsumer] Intento de conexión...")
        
        try:
            # Grupo general de usuarios en línea
            self.room_group_name = 'users_online'
            
            # Obtener usuario del scope
            self.user = self.scope.get('user')
            print(f"🔵 Usuario: {self.user}")
            print(f"🔵 Autenticado: {self.user.is_authenticated if self.user else 'No user'}")
            
            # Únete al grupo
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # IMPORTANTE: Acepta la conexión SIEMPRE
            await self.accept()
            print("✅ Conexión WebSocket ACEPTADA")
            
            # Obtener datos del usuario
            user_data = None
            if self.user and self.user.is_authenticated:
                try:
                    user_data = await self.get_user_data(self.user)
                    
                    # Registrar conexión
                    UsersOnlineConsumer.connected_users[self.channel_name] = {
                        'user_id': self.user.id,
                        'user_data': user_data,
                        'channel_name': self.channel_name
                    }
                    
                    print(f"✅ Usuario registrado: {user_data['name']} (ID: {self.user.id})")
                    print(f"📊 Total usuarios conectados: {len(UsersOnlineConsumer.connected_users)}")
                    
                    # Notificar a todos
                    await self.broadcast_users_update()
                except Exception as e:
                    print(f"⚠️ Error al obtener datos del usuario: {e}")
            else:
                print("⚠️ Usuario no autenticado o anónimo")
            
            # Enviar mensaje de bienvenida
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Conectado al sistema de usuarios en línea',
                'user': user_data,
                'is_authenticated': self.user.is_authenticated if self.user else False,
                'timestamp': self.get_timestamp()
            }))
            
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ ERROR EN CONNECT: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            print("=" * 50)
    
    async def disconnect(self, close_code):
        """Se ejecuta cuando un cliente se desconecta"""
        print(f"🔴 Desconexión - Código: {close_code}")
        
        try:
            if self.channel_name in UsersOnlineConsumer.connected_users:
                user_info = UsersOnlineConsumer.connected_users[self.channel_name]
                print(f"❌ Usuario desconectado: {user_info['user_data']['name']}")
                
                del UsersOnlineConsumer.connected_users[self.channel_name]
                await self.broadcast_users_update()
            
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
        except Exception as e:
            print(f"❌ Error en disconnect: {e}")
    
    async def receive(self, text_data):
        """Recibe mensajes del WebSocket desde el cliente"""
        print(f"📨 Mensaje recibido: {text_data}")
        
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'message': 'pong',
                    'timestamp': self.get_timestamp()
                }))
            
            elif message_type == 'get_connected_users':
                await self.send_connected_users()
            
        except Exception as e:
            print(f"❌ Error en receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e),
                'timestamp': self.get_timestamp()
            }))
    
    async def users_update(self, event):
        """Envía actualización de usuarios conectados a todos"""
        await self.send(text_data=json.dumps({
            'type': 'users_update',
            'users': event['users'],
            'total': event['total'],
            'timestamp': self.get_timestamp()
        }))
    
    async def broadcast_users_update(self):
        """Envía la lista actualizada de usuarios a todos los conectados"""
        users_list = self.get_unique_users_list()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'users_update',
                'users': users_list,
                'total': len(users_list)
            }
        )
    
    async def send_connected_users(self):
        """Envía la lista de usuarios conectados solo al solicitante"""
        users_list = self.get_unique_users_list()
        
        await self.send(text_data=json.dumps({
            'type': 'users_update',
            'users': users_list,
            'total': len(users_list),
            'timestamp': self.get_timestamp()
        }))
    
    def get_unique_users_list(self):
        """Obtiene lista única de usuarios"""
        unique_users = {}
        for channel_data in UsersOnlineConsumer.connected_users.values():
            user_id = channel_data['user_id']
            if user_id not in unique_users:
                unique_users[user_id] = channel_data['user_data']
        
        return list(unique_users.values())
    
    @database_sync_to_async
    def get_user_data(self, user):
        """Obtiene datos del usuario"""
        return {
            'id': user.id,
            'username': user.username,
            'name': user.get_full_name() if user.get_full_name() else user.username,
            'email': user.email,
            'first_name': getattr(user, 'first_name', ''),
            'last_name': getattr(user, 'last_name', ''),
            'role': getattr(user, 'role', 'user'),
            'role_display': user.get_role_display() if hasattr(user, 'get_role_display') else 'Usuario',
            'image': user.image.url if hasattr(user, 'image') and user.image else None,
            'initials': self.get_initials(user),
            'status': 'online'
        }
    
    @staticmethod
    def get_initials(user):
        """Genera iniciales del usuario"""
        try:
            first = getattr(user, 'first_name', '')
            last = getattr(user, 'last_name', '')
            
            if first and last:
                return f"{first[0]}{last[0]}".upper()
            elif first:
                return first[0:2].upper()
            elif hasattr(user, 'username'):
                return user.username[0:2].upper()
            else:
                return 'U'
        except:
            return 'U'
    
    @staticmethod
    def get_timestamp():
        """Retorna timestamp ISO"""
        from datetime import datetime
        return datetime.now().isoformat()