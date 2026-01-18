# liquidacion/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError, transaction
from django.db.models import Q, Sum, Avg
from datetime import datetime
from decimal import Decimal

from liquidacion.models import Liquidacion
from user.api.permissions import RolePermission


# ✅ Listar liquidaciones
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_liquidaciones(request):
    """
    Lista todas las liquidaciones con filtros opcionales.
    """
    try:
        # QuerySet base
        liquidaciones = Liquidacion.objects.select_related(
            'preparacion',
            'tramite',
            'proveedor',
            'cliente',
            'departamento',
            'municipio'
        ).all()

        # --- Filtros ---
        # Filtro de búsqueda general
        search_query = request.query_params.get('search', None)
        if search_query:
            liquidaciones = liquidaciones.filter(
                Q(placa__icontains=search_query) |
                Q(tramite__nombre__icontains=search_query) |
                Q(proveedor__nombre__icontains=search_query) |
                Q(proveedor__codigo_encargado__icontains=search_query) |
                Q(cliente__nombre__icontains=search_query) |
                Q(departamento__departamento__icontains=search_query) |
                Q(municipio__municipio__icontains=search_query)
            )

        # Filtro por estado
        estado_filter = request.query_params.get('estado', None)
        if estado_filter:
            liquidaciones = liquidaciones.filter(estado=estado_filter)

        # Filtro por proveedor
        proveedor_filter = request.query_params.get('proveedor', None)
        if proveedor_filter:
            liquidaciones = liquidaciones.filter(proveedor_id=proveedor_filter)

        # Filtro por tramite
        tramite_filter = request.query_params.get('tramite', None)
        if tramite_filter:
            liquidaciones = liquidaciones.filter(tramite_id=tramite_filter)

        # Filtro por departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            liquidaciones = liquidaciones.filter(departamento_id=departamento_filter)

        # Filtro por municipio
        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            liquidaciones = liquidaciones.filter(municipio_id=municipio_filter)

        # Filtros de fecha
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            liquidaciones = liquidaciones.filter(fecha_finalizado__date__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            liquidaciones = liquidaciones.filter(fecha_finalizado__date__lte=end_date)

        # Construir respuesta
        liquidaciones_data = []
        for liq in liquidaciones.order_by('-fecha_finalizado'):
            liquidaciones_data.append({
                'id': liq.id,
                'preparacion_id': liq.preparacion_id,
                'placa': liq.placa,
                'tipo_vehiculo': liq.tipo_vehiculo,

                # Trámite
                'tramite_id': liq.tramite_id,
                'tramite_nombre': liq.tramite.nombre if liq.tramite else None,

                # Proveedor/Gestor
                'proveedor_id': liq.proveedor_id,
                'proveedor_nombre': liq.proveedor.nombre if liq.proveedor else None,
                'proveedor_codigo': liq.proveedor.codigo_encargado if liq.proveedor else None,

                # Cliente
                'cliente_id': liq.cliente_id,
                'cliente_nombre': liq.cliente.nombre if liq.cliente else None,

                # Ubicación
                'departamento_id': liq.departamento_id,
                'departamento_nombre': liq.departamento.departamento if liq.departamento else None,
                'municipio_id': liq.municipio_id,
                'municipio_nombre': liq.municipio.municipio if liq.municipio else None,

                # Datos económicos - Facturación
                'derechos_tramite': str(liq.derechos_tramite),
                'servicio_empresa': str(liq.servicio_empresa),
                'iva_servicio': str(liq.iva_servicio),
                'total_facturacion': str(liq.total_facturacion),
                'total_facturacion_sin_iva': str(liq.total_facturacion_sin_iva),

                # Datos económicos - Servicio Gestor
                'servicio_gestor': str(liq.servicio_gestor),
                'transporte': str(liq.transporte),
                'bonificacion': str(liq.bonificacion),
                'anticipos': str(liq.anticipos),
                'total_servicio_gestor': str(liq.total_servicio_gestor),

                # Utilidad
                'utilidad': str(liq.utilidad),
                'es_rentable': liq.es_rentable,

                # Estado y fechas
                'estado': liq.estado,
                'observaciones': liq.observaciones,
                'fecha_finalizado': liq.fecha_finalizado.isoformat() if liq.fecha_finalizado else None,
                'created_at': liq.created_at.isoformat() if liq.created_at else None,
                'updated_at': liq.updated_at.isoformat() if liq.updated_at else None,
            })

        # Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(liquidaciones_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response(
            {"error": f"Error al listar liquidaciones: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener liquidación por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_liquidacion(request, pk):
    """
    Obtiene una liquidación específica por su ID.
    """
    try:
        liq = get_object_or_404(
            Liquidacion.objects.select_related(
                'preparacion',
                'tramite',
                'proveedor',
                'cliente',
                'departamento',
                'municipio'
            ),
            pk=pk
        )

        data = {
            'id': liq.id,
            'preparacion_id': liq.preparacion_id,
            'placa': liq.placa,
            'tipo_vehiculo': liq.tipo_vehiculo,

            # Trámite
            'tramite_id': liq.tramite_id,
            'tramite_nombre': liq.tramite.nombre if liq.tramite else None,

            # Proveedor/Gestor
            'proveedor_id': liq.proveedor_id,
            'proveedor_nombre': liq.proveedor.nombre if liq.proveedor else None,
            'proveedor_codigo': liq.proveedor.codigo_encargado if liq.proveedor else None,

            # Cliente
            'cliente_id': liq.cliente_id,
            'cliente_nombre': liq.cliente.nombre if liq.cliente else None,

            # Ubicación
            'departamento_id': liq.departamento_id,
            'departamento_nombre': liq.departamento.departamento if liq.departamento else None,
            'municipio_id': liq.municipio_id,
            'municipio_nombre': liq.municipio.municipio if liq.municipio else None,

            # Datos económicos - Facturación
            'derechos_tramite': str(liq.derechos_tramite),
            'servicio_empresa': str(liq.servicio_empresa),
            'iva_servicio': str(liq.iva_servicio),
            'total_facturacion': str(liq.total_facturacion),
            'total_facturacion_sin_iva': str(liq.total_facturacion_sin_iva),

            # Datos económicos - Servicio Gestor
            'servicio_gestor': str(liq.servicio_gestor),
            'transporte': str(liq.transporte),
            'bonificacion': str(liq.bonificacion),
            'anticipos': str(liq.anticipos),
            'total_servicio_gestor': str(liq.total_servicio_gestor),

            # Utilidad
            'utilidad': str(liq.utilidad),
            'es_rentable': liq.es_rentable,

            # Estado y fechas
            'estado': liq.estado,
            'observaciones': liq.observaciones,
            'fecha_finalizado': liq.fecha_finalizado.isoformat() if liq.fecha_finalizado else None,
            'created_at': liq.created_at.isoformat() if liq.created_at else None,
            'updated_at': liq.updated_at.isoformat() if liq.updated_at else None,
        }

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al obtener liquidación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar liquidación (valores económicos editables)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_liquidacion(request, pk):
    """
    Actualiza los valores económicos de una liquidación.
    """
    try:
        liq = get_object_or_404(Liquidacion, pk=pk)
        data = request.data

        # Campos editables
        if 'derechos_tramite' in data:
            liq.derechos_tramite = Decimal(str(data['derechos_tramite']))
        if 'servicio_empresa' in data:
            liq.servicio_empresa = Decimal(str(data['servicio_empresa']))
        if 'servicio_gestor' in data:
            liq.servicio_gestor = Decimal(str(data['servicio_gestor']))
        if 'transporte' in data:
            liq.transporte = Decimal(str(data['transporte']))
        if 'bonificacion' in data:
            liq.bonificacion = Decimal(str(data['bonificacion']))
        if 'anticipos' in data:
            liq.anticipos = Decimal(str(data['anticipos']))
        if 'estado' in data:
            liq.estado = data['estado']
        if 'observaciones' in data:
            liq.observaciones = data['observaciones']

        liq.save()

        return Response({
            "message": "Liquidación actualizada exitosamente",
            "id": liq.id,
            "placa": liq.placa,
            "utilidad": str(liq.utilidad),
            "es_rentable": liq.es_rentable,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al actualizar liquidación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener estadísticas de liquidaciones
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_estadisticas(request):
    """
    Obtiene estadísticas generales de las liquidaciones.
    """
    try:
        # Filtros de fecha opcionales
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        liquidaciones = Liquidacion.objects.all()

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            liquidaciones = liquidaciones.filter(fecha_finalizado__date__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            liquidaciones = liquidaciones.filter(fecha_finalizado__date__lte=end_date)

        # Totales
        total_liquidaciones = liquidaciones.count()

        # Calcular totales manualmente usando properties
        total_facturacion = Decimal('0')
        total_servicio_gestor = Decimal('0')
        total_utilidad = Decimal('0')
        rentables = 0
        no_rentables = 0

        for liq in liquidaciones:
            total_facturacion += liq.total_facturacion_sin_iva
            total_servicio_gestor += liq.total_servicio_gestor
            total_utilidad += liq.utilidad
            if liq.es_rentable:
                rentables += 1
            else:
                no_rentables += 1

        # Por estado
        por_estado = {}
        for estado, _ in Liquidacion.ESTADO_CHOICES:
            por_estado[estado] = liquidaciones.filter(estado=estado).count()

        data = {
            'total_liquidaciones': total_liquidaciones,
            'total_facturacion': str(total_facturacion),
            'total_servicio_gestor': str(total_servicio_gestor),
            'total_utilidad': str(total_utilidad),
            'tramites_rentables': rentables,
            'tramites_no_rentables': no_rentables,
            'porcentaje_rentabilidad': round((rentables / total_liquidaciones * 100), 2) if total_liquidaciones > 0 else 0,
            'por_estado': por_estado,
        }

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al obtener estadísticas: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener liquidación por preparacion_id
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_liquidacion_by_preparacion(request, preparacion_id):
    """
    Obtiene la liquidación asociada a un trámite de preparación.
    """
    try:
        liq = get_object_or_404(
            Liquidacion.objects.select_related(
                'preparacion',
                'tramite',
                'proveedor',
                'cliente',
                'departamento',
                'municipio'
            ),
            preparacion_id=preparacion_id
        )

        data = {
            'id': liq.id,
            'preparacion_id': liq.preparacion_id,
            'placa': liq.placa,
            'tipo_vehiculo': liq.tipo_vehiculo,

            # Trámite
            'tramite_id': liq.tramite_id,
            'tramite_nombre': liq.tramite.nombre if liq.tramite else None,

            # Proveedor/Gestor
            'proveedor_id': liq.proveedor_id,
            'proveedor_nombre': liq.proveedor.nombre if liq.proveedor else None,
            'proveedor_codigo': liq.proveedor.codigo_encargado if liq.proveedor else None,

            # Cliente
            'cliente_id': liq.cliente_id,
            'cliente_nombre': liq.cliente.nombre if liq.cliente else None,

            # Ubicación
            'departamento_id': liq.departamento_id,
            'departamento_nombre': liq.departamento.departamento if liq.departamento else None,
            'municipio_id': liq.municipio_id,
            'municipio_nombre': liq.municipio.municipio if liq.municipio else None,

            # Datos económicos
            'derechos_tramite': str(liq.derechos_tramite),
            'servicio_empresa': str(liq.servicio_empresa),
            'iva_servicio': str(liq.iva_servicio),
            'total_facturacion': str(liq.total_facturacion),
            'total_facturacion_sin_iva': str(liq.total_facturacion_sin_iva),
            'servicio_gestor': str(liq.servicio_gestor),
            'transporte': str(liq.transporte),
            'bonificacion': str(liq.bonificacion),
            'anticipos': str(liq.anticipos),
            'total_servicio_gestor': str(liq.total_servicio_gestor),
            'utilidad': str(liq.utilidad),
            'es_rentable': liq.es_rentable,

            # Estado y fechas
            'estado': liq.estado,
            'observaciones': liq.observaciones,
            'fecha_finalizado': liq.fecha_finalizado.isoformat() if liq.fecha_finalizado else None,
            'created_at': liq.created_at.isoformat() if liq.created_at else None,
            'updated_at': liq.updated_at.isoformat() if liq.updated_at else None,
        }

        return Response(data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al obtener liquidación: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
