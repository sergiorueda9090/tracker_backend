# proveedores/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError
from django.db.models import Q, Subquery, OuterRef
from datetime import datetime
import json

from proveedores.models import Proveedor
from user.api.permissions import RolePermission
from departamentos.models import Departamento
from municipios.models import Municipio


# ✅ Crear proveedor
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_proveedor(request):
    try:
        # Detectar si es JSON o form-data
        if request.content_type == 'application/json':
            data = request.data
        else:
            data = request.data.copy()
            
            if 'transitos_habilitados' in data and isinstance(data['transitos_habilitados'], str):
                try:
                    data['transitos_habilitados'] = json.loads(data['transitos_habilitados'])
                except json.JSONDecodeError:
                    data['transitos_habilitados'] = []

        codigo_encargado = data.get('codigo_encargado')
        nombre = data.get('nombre')
        whatsapp = data.get('whatsapp', '')
        departamento = data.get('departamento', '')
        municipio = data.get('municipio', '')
        transitos_habilitados = data.get('transitos_habilitados', [])
        
        if not codigo_encargado or not nombre:
            return Response(
                {"error": "codigo_encargado y nombre son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if Proveedor.objects.filter(codigo_encargado=codigo_encargado).exists():
            return Response(
                {"error": "Ya existe un proveedor con este código de encargado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        proveedor = Proveedor.objects.create(
            user=request.user,
            codigo_encargado=codigo_encargado,
            nombre=nombre,
            whatsapp=whatsapp,
            departamento=departamento,
            municipio=municipio,
            transitos_habilitados=transitos_habilitados
        )

        response_data = {
            "id": proveedor.id,
            "codigo_encargado": proveedor.codigo_encargado,
            "nombre": proveedor.nombre,
            "departamento": proveedor.departamento,
            "municipio": proveedor.municipio
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar proveedores
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_proveedores(request):
    try:
        # 1. Definir Subconsultas para obtener los nombres
        # Buscamos en la tabla Departamento donde el id coincide con el valor guardado en Proveedor
        nombre_depto_subquery = Departamento.objects.filter(
            id_departamento=OuterRef('departamento')
        ).values('departamento')[:1]

        # Buscamos en la tabla Municipio donde el id coincide con el valor guardado en Proveedor
        nombre_muni_subquery = Municipio.objects.filter(
            id_municipio=OuterRef('municipio')
        ).values('municipio')[:1]

        # 2. QuerySet Base con Annotation
        # Usamos annotate para crear campos virtuales 'nombre_depto' y 'nombre_muni'
        proveedores = Proveedor.objects.select_related('user').annotate(
            nombre_depto=Subquery(nombre_depto_subquery),
            nombre_muni=Subquery(nombre_muni_subquery)
        ).all()

        # --- Filtro de Buscador (Search) ---
        search_query = request.query_params.get('search', None)
        if search_query:
            proveedores = proveedores.filter(
                Q(codigo_encargado__icontains=search_query) |
                Q(nombre__icontains=search_query) |
                Q(whatsapp__icontains=search_query) |
                Q(nombre_depto__icontains=search_query) | # Ahora puedes buscar por nombre de texto
                Q(nombre_muni__icontains=search_query)
            )

        # --- Filtros de Estado, Depto y Muni ---
        #status_filter = request.query_params.get('status', None)
        #if status_filter not in [None, '']:
        #    proveedores = proveedores.filter(is_active=(status_filter == '1'))

        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            proveedores = proveedores.filter(departamento=departamento_filter)

        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            proveedores = proveedores.filter(municipio=municipio_filter)

        # --- Filtros de Fecha ---
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            proveedores = proveedores.filter(created_at__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            from datetime import datetime as dt, time
            end_date_inclusive = dt.combine(end_date, time.max)
            proveedores = proveedores.filter(created_at__lte=end_date_inclusive)

        # 3. Selección de campos (Values)
        # Incluimos los campos originales (IDs) y los anotados (Nombres)
        proveedores_data = proveedores.order_by('-id').values(
            'id',
            'codigo_encargado',
            'nombre',
            'whatsapp',
            'departamento',        # Este es el ID (ej: "05")
            'municipio',           # Este es el ID (ej: "05001")
            'nombre_depto',        # Este es el Nombre (ej: "Antioquia")
            'nombre_muni',         # Este es el Nombre (ej: "Medellín")
            'transitos_habilitados',
            'is_active',
            'created_at',
        )

        # 4. Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size
        
        paginated_queryset = paginator.paginate_queryset(proveedores_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# ✅ Obtener proveedor por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_proveedor(request, pk):
    try:
        proveedor = get_object_or_404(Proveedor, pk=pk)
        data = {
            "id": proveedor.id,
            "codigo_encargado": proveedor.codigo_encargado,
            "nombre": proveedor.nombre,
            "whatsapp": proveedor.whatsapp,
            "departamento": proveedor.departamento,
            "municipio": proveedor.municipio,
            "transitos_habilitados": proveedor.transitos_habilitados,
            "is_active": proveedor.is_active,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving proveedor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar proveedor
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_proveedor(request, pk):
    try:
        proveedor = get_object_or_404(Proveedor, pk=pk)
        
        if request.content_type == 'application/json':
            data = request.data
        else:
            data = request.data.copy()
            
            if 'transitos_habilitados' in data and isinstance(data['transitos_habilitados'], str):
                try:
                    data['transitos_habilitados'] = json.loads(data['transitos_habilitados'])
                except json.JSONDecodeError:
                    data['transitos_habilitados'] = []

        proveedor.codigo_encargado = data.get('codigo_encargado', proveedor.codigo_encargado)
        proveedor.nombre = data.get('nombre', proveedor.nombre)
        proveedor.whatsapp = data.get('whatsapp', proveedor.whatsapp)
        proveedor.departamento = data.get('departamento', proveedor.departamento)
        proveedor.municipio = data.get('municipio', proveedor.municipio)
        proveedor.transitos_habilitados = data.get('transitos_habilitados', proveedor.transitos_habilitados)

        if 'is_active' in data:
            proveedor.is_active = bool(int(data.get('is_active')))

        proveedor.save()

        response_data = {
            "id": proveedor.id,
            "codigo_encargado": proveedor.codigo_encargado,
            "nombre": proveedor.nombre,
            "departamento": proveedor.departamento,
            "municipio": proveedor.municipio,
            "is_active": proveedor.is_active,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error while updating proveedor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar proveedor
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_proveedor(request, pk):
    try:
        proveedor = get_object_or_404(Proveedor, pk=pk)
        proveedor.delete()
        return Response(
            {"message": "Proveedor deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error deleting proveedor: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )