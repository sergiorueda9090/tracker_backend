from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from django.db import DatabaseError
from departamentos.models import Departamento
from user.api.permissions import RolePermission
from django.db.models import Q # Importar Q para búsquedas complejas
from datetime import datetime  # Importar datetime para manejar fechas


@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_departamentos(request):
    try:
        print("Rol del usuario:", request.user.role)

        # 1. Obtener todos los usuarios como un queryset
        departamentos = Departamento.objects.all()


        return Response(
            {
                "departamentos": [
                    {
                        "id_departamento": depto.id_departamento,
                        "departamento": depto.departamento,
                    }
                    for depto in departamentos
                ]
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        print(f"Error en list_users: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error fetching users: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
