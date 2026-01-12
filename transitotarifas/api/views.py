# transitotarifas/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError
from django.db.models import Q
from datetime import datetime

from transitotarifas.models import TransitoTarifa
from tramites.models import Tramite
from proveedores.models import Proveedor
from user.api.permissions import RolePermission


# ✅ Crear tránsito tarifa
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_transito_tarifa(request):
    try:
        data = request.data

        tramite_id = data.get('tramite_id')
        proveedor_id = data.get('proveedor_id')
        servicio_proveedor = data.get('servicio_proveedor')
        servicio_empresa = data.get('servicio_empresa')

        # Validaciones
        if not tramite_id:
            return Response(
                {"error": "El trámite es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not proveedor_id:
            return Response(
                {"error": "El proveedor es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not servicio_proveedor:
            return Response(
                {"error": "El servicio del proveedor es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not servicio_empresa:
            return Response(
                {"error": "El servicio de la empresa es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que los precios sean números válidos
        try:
            servicio_proveedor = float(servicio_proveedor)
            servicio_empresa = float(servicio_empresa)

            if servicio_proveedor < 0 or servicio_empresa < 0:
                return Response(
                    {"error": "Los precios no pueden ser negativos."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Los precios deben ser números válidos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que existan el trámite y el proveedor
        try:
            tramite = Tramite.objects.get(pk=tramite_id)
        except Tramite.DoesNotExist:
            return Response(
                {"error": "El trámite especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            proveedor = Proveedor.objects.get(pk=proveedor_id)
        except Proveedor.DoesNotExist:
            return Response(
                {"error": "El proveedor especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si ya existe esta combinación
        if TransitoTarifa.objects.filter(tramite=tramite, proveedor=proveedor).exists():
            return Response(
                {"error": "Ya existe una tarifa para este trámite y proveedor."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear la tarifa
        transito_tarifa = TransitoTarifa.objects.create(
            tramite=tramite,
            proveedor=proveedor,
            servicio_proveedor=servicio_proveedor,
            servicio_empresa=servicio_empresa
        )

        response_data = {
            "id": transito_tarifa.id,
            "tramite_id": transito_tarifa.tramite.id,
            "tramite_nombre": transito_tarifa.tramite.nombre,
            "proveedor_id": transito_tarifa.proveedor.id,
            "proveedor_nombre": transito_tarifa.proveedor.nombre,
            "proveedor_codigo": transito_tarifa.proveedor.codigo_encargado,
            "servicio_proveedor": str(transito_tarifa.servicio_proveedor),
            "servicio_empresa": str(transito_tarifa.servicio_empresa),
            "margen_ganancia": str(transito_tarifa.margen_ganancia),
            "porcentaje_margen": round(transito_tarifa.porcentaje_margen, 2),
            "is_active": transito_tarifa.is_active,
            "created_at": transito_tarifa.created_at,
            "updated_at": transito_tarifa.updated_at,
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


# ✅ Listar tránsitos tarifas
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_transito_tarifas(request):
    try:
        # QuerySet base con relaciones
        transito_tarifas = TransitoTarifa.objects.select_related('tramite', 'proveedor').all()

        # Filtro de búsqueda
        search_query = request.query_params.get('search', None)
        if search_query:
            transito_tarifas = transito_tarifas.filter(
                Q(tramite__nombre__icontains=search_query) |
                Q(proveedor__nombre__icontains=search_query) |
                Q(proveedor__codigo_encargado__icontains=search_query)
            )

        # Filtro por trámite
        tramite_filter = request.query_params.get('tramite', None)
        if tramite_filter:
            transito_tarifas = transito_tarifas.filter(tramite_id=tramite_filter)

        # Filtro por proveedor
        proveedor_filter = request.query_params.get('proveedor', None)
        if proveedor_filter:
            transito_tarifas = transito_tarifas.filter(proveedor_id=proveedor_filter)

        # Filtro por estado
        status_filter = request.query_params.get('status', None)
        if status_filter not in [None, '']:
            transito_tarifas = transito_tarifas.filter(is_active=(status_filter == '1'))

        # Filtros de fecha
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            transito_tarifas = transito_tarifas.filter(created_at__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            from datetime import datetime as dt, time
            end_date_inclusive = dt.combine(end_date, time.max)
            transito_tarifas = transito_tarifas.filter(created_at__lte=end_date_inclusive)

        # Ordenar y seleccionar campos
        transito_tarifas_data = transito_tarifas.order_by('tramite__nombre', 'proveedor__nombre').values(
            'id',
            'tramite_id',
            'tramite__nombre',
            'proveedor_id',
            'proveedor__nombre',
            'proveedor__codigo_encargado',
            'servicio_proveedor',
            'servicio_empresa',
            'is_active',
            'created_at',
            'updated_at',
        )

        # Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(transito_tarifas_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener tránsito tarifa por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transito_tarifa(request, pk):
    try:
        transito_tarifa = get_object_or_404(
            TransitoTarifa.objects.select_related('tramite', 'proveedor'),
            pk=pk
        )
        data = {
            "id": transito_tarifa.id,
            "tramite_id": transito_tarifa.tramite.id,
            "tramite_nombre": transito_tarifa.tramite.nombre,
            "proveedor_id": transito_tarifa.proveedor.id,
            "proveedor_nombre": transito_tarifa.proveedor.nombre,
            "proveedor_codigo": transito_tarifa.proveedor.codigo_encargado,
            "servicio_proveedor": str(transito_tarifa.servicio_proveedor),
            "servicio_empresa": str(transito_tarifa.servicio_empresa),
            "margen_ganancia": str(transito_tarifa.margen_ganancia),
            "porcentaje_margen": round(transito_tarifa.porcentaje_margen, 2),
            "is_active": transito_tarifa.is_active,
            "created_at": transito_tarifa.created_at,
            "updated_at": transito_tarifa.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error al obtener tránsito tarifa: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar tránsito tarifa
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_transito_tarifa(request, pk):
    try:
        transito_tarifa = get_object_or_404(TransitoTarifa, pk=pk)
        data = request.data

        # Actualizar trámite si se proporciona
        tramite_id = data.get('tramite_id')
        if tramite_id and tramite_id != transito_tarifa.tramite.id:
            try:
                tramite = Tramite.objects.get(pk=tramite_id)

                # Verificar que no exista la combinación nueva
                if TransitoTarifa.objects.filter(
                    tramite=tramite,
                    proveedor=transito_tarifa.proveedor
                ).exclude(pk=pk).exists():
                    return Response(
                        {"error": "Ya existe una tarifa para este trámite y proveedor."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                transito_tarifa.tramite = tramite
            except Tramite.DoesNotExist:
                return Response(
                    {"error": "El trámite especificado no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar proveedor si se proporciona
        proveedor_id = data.get('proveedor_id')
        if proveedor_id and proveedor_id != transito_tarifa.proveedor.id:
            try:
                proveedor = Proveedor.objects.get(pk=proveedor_id)

                # Verificar que no exista la combinación nueva
                if TransitoTarifa.objects.filter(
                    tramite=transito_tarifa.tramite,
                    proveedor=proveedor
                ).exclude(pk=pk).exists():
                    return Response(
                        {"error": "Ya existe una tarifa para este trámite y proveedor."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                transito_tarifa.proveedor = proveedor
            except Proveedor.DoesNotExist:
                return Response(
                    {"error": "El proveedor especificado no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar servicio_proveedor si se proporciona
        if 'servicio_proveedor' in data:
            try:
                servicio_proveedor = float(data.get('servicio_proveedor'))
                if servicio_proveedor < 0:
                    return Response(
                        {"error": "El servicio del proveedor no puede ser negativo."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                transito_tarifa.servicio_proveedor = servicio_proveedor
            except (ValueError, TypeError):
                return Response(
                    {"error": "El servicio del proveedor debe ser un número válido."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar servicio_empresa si se proporciona
        if 'servicio_empresa' in data:
            try:
                servicio_empresa = float(data.get('servicio_empresa'))
                if servicio_empresa < 0:
                    return Response(
                        {"error": "El servicio de la empresa no puede ser negativo."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                transito_tarifa.servicio_empresa = servicio_empresa
            except (ValueError, TypeError):
                return Response(
                    {"error": "El servicio de la empresa debe ser un número válido."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Actualizar estado si se proporciona
        if 'is_active' in data:
            transito_tarifa.is_active = bool(int(data.get('is_active')))

        transito_tarifa.save()

        response_data = {
            "id": transito_tarifa.id,
            "tramite_id": transito_tarifa.tramite.id,
            "tramite_nombre": transito_tarifa.tramite.nombre,
            "proveedor_id": transito_tarifa.proveedor.id,
            "proveedor_nombre": transito_tarifa.proveedor.nombre,
            "proveedor_codigo": transito_tarifa.proveedor.codigo_encargado,
            "servicio_proveedor": str(transito_tarifa.servicio_proveedor),
            "servicio_empresa": str(transito_tarifa.servicio_empresa),
            "margen_ganancia": str(transito_tarifa.margen_ganancia),
            "porcentaje_margen": round(transito_tarifa.porcentaje_margen, 2),
            "is_active": transito_tarifa.is_active,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Error de base de datos al actualizar tránsito tarifa: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Error inesperado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar tránsito tarifa
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_transito_tarifa(request, pk):
    try:
        transito_tarifa = get_object_or_404(TransitoTarifa, pk=pk)
        transito_tarifa.delete()
        return Response(
            {"message": "Tránsito tarifa eliminada exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error al eliminar tránsito tarifa: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
