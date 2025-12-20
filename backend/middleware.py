# backend/middleware.py
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_key):
    """Obtiene el usuario desde el token JWT"""
    try:
        # Limpiar el token (remover "Bearer " si existe)
        token_key = token_key.strip()
        if token_key.startswith('Bearer '):
            token_key = token_key[7:]
        
        print(f"🔐 Procesando token...")
        print(f"   Token (primeros 30 chars): {token_key[:30]}...")
        
        # Decodificar el token
        access_token = AccessToken(token_key)
        user_id = access_token['user_id']
        
        print(f"✅ Token decodificado exitosamente")
        print(f"   User ID: {user_id}")
        
        # Obtener el usuario
        user = User.objects.get(id=user_id)
        print(f"✅ Usuario autenticado: {user.username} (ID: {user.id}, Role: {user.role})")
        
        return user
        
    except Exception as e:
        print(f"❌ Error al autenticar token:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Middleware personalizado para autenticación JWT en WebSockets"""
    
    async def __call__(self, scope, receive, send):
        print("\n" + "=" * 60)
        print("🔍 JWTAuthMiddleware - Iniciando autenticación WebSocket")
        print("=" * 60)
        
        # Obtener el token de la query string
        query_string = scope.get('query_string', b'').decode()
        print(f"📋 Query string completo: {query_string[:100]}...")
        
        query_params = parse_qs(query_string)
        
        token = None
        
        # Buscar el token en query params
        if 'token' in query_params:
            token = query_params['token'][0]
            print(f"✅ Token encontrado en query params")
            print(f"   Longitud del token: {len(token)} caracteres")
        else:
            print(f"❌ No se encontró 'token' en query params")
            print(f"   Parámetros disponibles: {list(query_params.keys())}")
        
        # Autenticar
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
            print("⚠️ Usuario establecido como AnonymousUser")
        
        print(f"👤 Usuario final: {scope['user']}")
        print(f"   Autenticado: {scope['user'].is_authenticated if scope['user'] else False}")
        print("=" * 60 + "\n")
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Stack de middleware para JWT"""
    return JWTAuthMiddleware(inner)