from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import make_password
from django.db import DatabaseError
from departamentos.models import Departamento
from municipios.models import Municipio
from user.api.permissions import RolePermission
from django.db.models import Q # Importar Q para búsquedas complejas
from datetime import datetime  # Importar datetime para manejar fechas


@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_municipios(request, id_departamento=None):
    try:
       # 1. Obtener todos los usuarios como un queryset
        municipios = Departamento.objects.filter(id_departamento=id_departamento).first()
        municipios = Municipio.objects.filter(departamento=municipios)

        return Response(
            {
                "municipios": [
                    {
                        "id_municipio": municipio.id_municipio,
                        "municipio": municipio.municipio,
                    }
                    for municipio in municipios
                ]
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error fetching users: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
