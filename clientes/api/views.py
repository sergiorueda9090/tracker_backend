# clientes/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError
from django.db.models import Q
from datetime import datetime

from clientes.models import Cliente
from user.api.permissions import RolePermission
from departamentos.models import Departamento
from municipios.models import Municipio


# ✅ Crear cliente
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_cliente(request):
    try:
        data = request.data

        nombre = data.get('nombre')
        razon_social = data.get('razon_social')
        nit = data.get('nit')
        departamento_id = data.get('departamento_id')
        ciudad_id = data.get('ciudad_id')

        # Validaciones
        if not all([nombre, razon_social, nit, departamento_id, ciudad_id]):
            return Response(
                {"error": "Todos los campos son requeridos: nombre, razon_social, nit, departamento_id, ciudad_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si el NIT ya existe
        if Cliente.objects.filter(nit=nit).exists():
            return Response(
                {"error": "Ya existe un cliente con este NIT."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que existan el departamento y ciudad
        try:
            departamento = Departamento.objects.get(id_departamento=departamento_id)
        except Departamento.DoesNotExist:
            return Response(
                {"error": "El departamento especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ciudad = Municipio.objects.get(id_municipio=ciudad_id)
        except Municipio.DoesNotExist:
            return Response(
                {"error": "La ciudad especificada no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear el cliente
        cliente = Cliente.objects.create(
            nombre=nombre,
            razon_social=razon_social,
            nit=nit,
            departamento=departamento,
            ciudad=ciudad
        )

        response_data = {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "razon_social": cliente.razon_social,
            "nit": cliente.nit,
            "departamento_id": cliente.departamento.id_departamento,
            "departamento_nombre": cliente.departamento.departamento,
            "ciudad_id": cliente.ciudad.id_municipio,
            "ciudad_nombre": cliente.ciudad.municipio,
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


# ✅ Listar clientes
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_clientes(request):
    try:
        # QuerySet base con relaciones
        clientes = Cliente.objects.select_related('departamento', 'ciudad').all()

        # Filtro de búsqueda
        search_query = request.query_params.get('search', None)
        if search_query:
            clientes = clientes.filter(
                Q(nombre__icontains=search_query) |
                Q(razon_social__icontains=search_query) |
                Q(nit__icontains=search_query) |
                Q(departamento__departamento__icontains=search_query) |
                Q(ciudad__municipio__icontains=search_query)
            )

        # Filtro por departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            clientes = clientes.filter(departamento_id=departamento_filter)

        # Filtro por ciudad
        ciudad_filter = request.query_params.get('ciudad', None)
        if ciudad_filter:
            clientes = clientes.filter(ciudad_id=ciudad_filter)

        # Filtro por estado
        status_filter = request.query_params.get('status', None)
        if status_filter not in [None, '']:
            clientes = clientes.filter(is_active=(status_filter == '1'))

        # Filtros de fecha
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            clientes = clientes.filter(created_at__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            from datetime import datetime as dt, time
            end_date_inclusive = dt.combine(end_date, time.max)
            clientes = clientes.filter(created_at__lte=end_date_inclusive)

        # Ordenar y seleccionar campos
        clientes_data = clientes.order_by('-id').values(
            'id',
            'nombre',
            'razon_social',
            'nit',
            'departamento_id',
            'departamento__departamento',
            'ciudad_id',
            'ciudad__municipio',
            'is_active',
            'created_at',
            'updated_at',
        )

        # Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(clientes_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener cliente por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_cliente(request, pk):
    try:
        cliente = get_object_or_404(Cliente.objects.select_related('departamento', 'ciudad'), pk=pk)
        data = {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "razon_social": cliente.razon_social,
            "nit": cliente.nit,
            "departamento_id": cliente.departamento.id_departamento,
            "departamento_nombre": cliente.departamento.departamento,
            "ciudad_id": cliente.ciudad.id_municipio,
            "ciudad_nombre": cliente.ciudad.municipio,
            "is_active": cliente.is_active,
            "created_at": cliente.created_at,
            "updated_at": cliente.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error al obtener cliente: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar cliente
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_cliente(request, pk):
    try:
        cliente = get_object_or_404(Cliente, pk=pk)
        data = request.data

        # Actualizar campos básicos
        cliente.nombre = data.get('nombre', cliente.nombre)
        cliente.razon_social = data.get('razon_social', cliente.razon_social)

        # Validar NIT único si se está cambiando
        new_nit = data.get('nit', cliente.nit)
        if new_nit != cliente.nit:
            if Cliente.objects.filter(nit=new_nit).exists():
                return Response(
                    {"error": "Ya existe un cliente con este NIT."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cliente.nit = new_nit

        # Actualizar departamento si se proporciona
        departamento_id = data.get('departamento_id')
        if departamento_id:
            try:
                departamento = Departamento.objects.get(id_departamento=departamento_id)
                cliente.departamento = departamento
            except Departamento.DoesNotExist:
                return Response(
                    {"error": "El departamento especificado no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar ciudad si se proporciona
        ciudad_id = data.get('ciudad_id')
        if ciudad_id:
            try:
                ciudad = Municipio.objects.get(id_municipio=ciudad_id)
                cliente.ciudad = ciudad
            except Municipio.DoesNotExist:
                return Response(
                    {"error": "La ciudad especificada no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar estado si se proporciona
        if 'is_active' in data:
            cliente.is_active = bool(int(data.get('is_active')))

        cliente.save()

        response_data = {
            "id": cliente.id,
            "nombre": cliente.nombre,
            "razon_social": cliente.razon_social,
            "nit": cliente.nit,
            "departamento_id": cliente.departamento.id_departamento,
            "departamento_nombre": cliente.departamento.departamento,
            "ciudad_id": cliente.ciudad.id_municipio,
            "ciudad_nombre": cliente.ciudad.municipio,
            "is_active": cliente.is_active,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Error de base de datos al actualizar cliente: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Error inesperado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar cliente
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_cliente(request, pk):
    try:
        cliente = get_object_or_404(Cliente, pk=pk)
        cliente.delete()
        return Response(
            {"message": "Cliente eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error al eliminar cliente: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
