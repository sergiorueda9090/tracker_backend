# tramites/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError
from django.db.models import Q
from datetime import datetime

from tramites.models import Tramite
from user.api.permissions import RolePermission


# ✅ Crear trámite
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_tramite(request):
    try:
        data = request.data

        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')

        # Validaciones
        if not nombre:
            return Response(
                {"error": "El nombre es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si el nombre ya existe
        if Tramite.objects.filter(nombre__iexact=nombre).exists():
            return Response(
                {"error": "Ya existe un trámite con este nombre."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el trámite
        tramite = Tramite.objects.create(
            nombre=nombre,
            descripcion=descripcion
        )

        response_data = {
            "id": tramite.id,
            "nombre": tramite.nombre,
            "descripcion": tramite.descripcion,
            "is_active": tramite.is_active,
            "created_at": tramite.created_at,
            "updated_at": tramite.updated_at,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    except DatabaseError as e:
        return Response(
            {"error": f"Error de base de datos: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Error inesperado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar trámites
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tramites(request):
    try:
        # QuerySet base
        tramites = Tramite.objects.all()

        # Filtro de búsqueda
        search_query = request.query_params.get('search', None)
        if search_query:
            tramites = tramites.filter(
                Q(nombre__icontains=search_query) |
                Q(descripcion__icontains=search_query)
            )

        # Filtro por estado
        status_filter = request.query_params.get('status', None)
        if status_filter not in [None, '']:
            tramites = tramites.filter(is_active=(status_filter == '1'))

        # Filtros de fecha
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            tramites = tramites.filter(created_at__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            from datetime import datetime as dt, time
            end_date_inclusive = dt.combine(end_date, time.max)
            tramites = tramites.filter(created_at__lte=end_date_inclusive)

        # Ordenar y seleccionar campos
        tramites_data = tramites.order_by('nombre').values(
            'id',
            'nombre',
            'descripcion',
            'is_active',
            'created_at',
            'updated_at',
        )

        # Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(tramites_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener trámite por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tramite(request, pk):
    try:
        tramite = get_object_or_404(Tramite, pk=pk)
        data = {
            "id": tramite.id,
            "nombre": tramite.nombre,
            "descripcion": tramite.descripcion,
            "is_active": tramite.is_active,
            "created_at": tramite.created_at,
            "updated_at": tramite.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error al obtener trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar trámite
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_tramite(request, pk):
    try:
        tramite = get_object_or_404(Tramite, pk=pk)
        data = request.data

        # Actualizar nombre si se proporciona
        new_nombre = data.get('nombre', tramite.nombre)
        if new_nombre != tramite.nombre:
            # Verificar que el nuevo nombre no exista
            if Tramite.objects.filter(nombre__iexact=new_nombre).exclude(pk=pk).exists():
                return Response(
                    {"error": "Ya existe un trámite con este nombre."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            tramite.nombre = new_nombre

        # Actualizar descripción
        if 'descripcion' in data:
            tramite.descripcion = data.get('descripcion', '')

        # Actualizar estado si se proporciona
        if 'is_active' in data:
            tramite.is_active = bool(int(data.get('is_active')))

        tramite.save()

        response_data = {
            "id": tramite.id,
            "nombre": tramite.nombre,
            "descripcion": tramite.descripcion,
            "is_active": tramite.is_active,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Error de base de datos al actualizar trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Error inesperado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar trámite
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_tramite(request, pk):
    try:
        tramite = get_object_or_404(Tramite, pk=pk)
        tramite.delete()
        return Response(
            {"message": "Trámite eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error al eliminar trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
