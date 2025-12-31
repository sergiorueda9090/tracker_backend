# tracker/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError, transaction
from django.db.models import Q, Subquery, OuterRef
from datetime import datetime

from preparacion.models import Preparacion, PreparacionArchivo
from user.api.permissions import RolePermission
from departamentos.models import Departamento
from municipios.models import Municipio
from proveedores.models import Proveedor
from tracker.websocket.utils import (
    notify_tracker_created,
    notify_tracker_updated,
    notify_tracker_deleted
)


# ✅ Crear trámite en tracker
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_tracker(request):
    try:
        with transaction.atomic():
            # 1. Extraer datos
            data = request.data

            # 2. Validaciones básicas
            placa           = data.get('placa')
            tipo_vehiculo   = data.get('tipo_vehiculo')
            departamento_id = data.get('departamento')
            municipio_id    = data.get('municipio')

            if not all([placa, tipo_vehiculo, departamento_id, municipio_id]):
                return Response(
                    {"error": "Placa, tipo de vehículo, departamento y municipio son requeridos."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2.1. Validar que el tipo de vehículo sea válido
            tipos_validos = [choice[0] for choice in Preparacion.TIPO_VEHICULO_CHOICES]
            if tipo_vehiculo not in tipos_validos:
                return Response(
                    {"error": f"Tipo de vehículo inválido. Valores permitidos: {', '.join(tipos_validos)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2.2. Validar que el departamento exista
            if not Departamento.objects.filter(id_departamento=departamento_id).exists():
                return Response(
                    {"error": f"El departamento con ID {departamento_id} no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2.3. Validar que el municipio exista
            if not Municipio.objects.filter(id_municipio=municipio_id).exists():
                return Response(
                    {"error": f"El municipio con ID {municipio_id} no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2.4. Validar proveedor (opcional)
            proveedor_id = data.get('proveedor', None)
            if proveedor_id and not Proveedor.objects.filter(id=proveedor_id).exists():
                return Response(
                    {"error": f"El proveedor con ID {proveedor_id} no existe."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. Preparar fecha de recepción (convertir string a date)
            fecha_recepcion = None
            fecha_str = data.get('fecha_recepcion_municipio', None)
            if fecha_str:
                try:
                    fecha_recepcion = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    return Response(
                        {"error": "Formato de fecha inválido. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 4. Crear el trámite (usando modelo Preparacion con estado_modulo=2)
            tracker = Preparacion.objects.create(
                usuario=request.user,
                placa=placa.upper(),
                tipo_vehiculo=tipo_vehiculo,
                departamento_id=departamento_id,
                municipio_id=municipio_id,
                estado=data.get('estado', 'en_radicacion'),  # Minúsculas
                estado_detalle=data.get('estado_detalle', ''),
                fecha_recepcion_municipio=fecha_recepcion,
                proveedor_id=proveedor_id,
                estado_modulo=2,  # CRÍTICO: Marca como módulo Tracker
                paquete=data.get('paquete', ''),
                lista_documentos=data.get('lista_documentos', [])
            )

            # 5. Construir datos para WebSocket
            tracker_data = {
                'id': tracker.id,
                'placa': tracker.placa,
                'tipo_vehiculo': tracker.tipo_vehiculo,
                'departamento': tracker.departamento_id,
                'municipio': tracker.municipio_id,
                'nombre_depto': tracker.departamento.departamento if tracker.departamento else None,
                'nombre_muni': tracker.municipio.municipio if tracker.municipio else None,
                'estado': tracker.estado,
                'estado_detalle': tracker.estado_detalle,
                'fecha_recepcion_municipio': tracker.fecha_recepcion_municipio.isoformat() if tracker.fecha_recepcion_municipio else None,
                'hace_dias': tracker.hace_dias,
                'proveedor_id': tracker.proveedor_id,
                'codigo_encargado': tracker.codigo_encargado,
                'proveedor_nombre': tracker.proveedor.nombre if tracker.proveedor else None,
                'usuario': tracker.usuario.username if tracker.usuario else 'Sin asignar',
                'created_at': tracker.created_at.isoformat(),
                'updated_at': tracker.updated_at.isoformat(),
            }

            # 6. Notificar vía WebSocket
            notify_tracker_created(tracker_data)

            return Response({
                "id": tracker.id,
                "placa": tracker.placa,
                "estado": tracker.estado,
            }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"❌ Error completo al crear tracker: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error inesperado al procesar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar trámites en tracker
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_trackers(request):
    try:
        # 1. Definir Subconsultas para obtener los nombres
        nombre_depto_subquery = Departamento.objects.filter(
            id_departamento=OuterRef('departamento')
        ).values('departamento')[:1]

        nombre_muni_subquery = Municipio.objects.filter(
            id_municipio=OuterRef('municipio')
        ).values('municipio')[:1]

        # 2. QuerySet Base con Annotation (filtrado por estado_modulo=2 para Tracker)
        trackers = Preparacion.objects.select_related(
            'usuario', 'departamento', 'municipio', 'proveedor'
        ).annotate(
            nombre_depto=Subquery(nombre_depto_subquery),
            nombre_muni=Subquery(nombre_muni_subquery)
        ).filter(estado_modulo=2)  # CRÍTICO: Solo registros del módulo Tracker

        # --- Filtros ---
        # Filtro de búsqueda general
        search_query = request.query_params.get('search', None)
        if search_query:
            trackers = trackers.filter(
                Q(placa__icontains=search_query) |
                Q(tipo_vehiculo__icontains=search_query) |
                Q(usuario__username__icontains=search_query) |
                Q(proveedor__codigo_encargado__icontains=search_query) |
                Q(proveedor__nombre__icontains=search_query) |
                Q(nombre_depto__icontains=search_query) |
                Q(nombre_muni__icontains=search_query)
            )

        # Filtro de estado
        estado_filter = request.query_params.get('estado', None)
        if estado_filter:
            trackers = trackers.filter(estado=estado_filter)

        # Filtro de tipo de vehículo
        tipo_vehiculo_filter = request.query_params.get('tipo_vehiculo', None)
        if tipo_vehiculo_filter:
            trackers = trackers.filter(tipo_vehiculo=tipo_vehiculo_filter)

        # Filtro de proveedor
        proveedor_filter = request.query_params.get('proveedor', None)
        if proveedor_filter:
            trackers = trackers.filter(proveedor_id=proveedor_filter)

        # Filtro de departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            trackers = trackers.filter(departamento_id=departamento_filter)

        # Filtro de municipio
        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            trackers = trackers.filter(municipio_id=municipio_filter)

        # Filtros de fecha de recepción
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            trackers = trackers.filter(fecha_recepcion_municipio__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            trackers = trackers.filter(fecha_recepcion_municipio__lte=end_date)

        # 3. Construir datos
        trackers_data = []
        for tracker in trackers.order_by('-created_at'):

            # Obtener archivos del trámite
            archivos = tracker.archivos.all().values(
                'id', 'nombre_original', 'tipo_archivo', 'tamaño', 'archivo', 'created_at'
            )

            archivos_list = [{
                "id": arch['id'],
                "nombre": arch['nombre_original'],
                "tipo": arch['tipo_archivo'],
                "tamaño": arch['tamaño'],
                "url": arch['archivo'],
                "created_at": arch['created_at']
            } for arch in archivos]

            trackers_data.append({
                'id': tracker.id,
                'placa': tracker.placa,
                'archivos': archivos_list,
                'total_archivos': len(archivos_list),
                'tipo_vehiculo': tracker.tipo_vehiculo,
                'departamento': tracker.departamento_id,
                'municipio': tracker.municipio_id,
                'nombre_depto': tracker.nombre_depto,
                'nombre_muni': tracker.nombre_muni,
                'estado': tracker.estado,
                'estado_detalle': tracker.estado_detalle,
                'estado_tracker': tracker.estado_tracker,
                'fecha_recepcion_municipio': tracker.fecha_recepcion_municipio,
                'hace_dias': tracker.hace_dias,
                'proveedor_id': tracker.proveedor_id,
                'codigo_encargado': tracker.codigo_encargado,
                'proveedor_nombre': tracker.proveedor.nombre if tracker.proveedor else None,
                'usuario': tracker.usuario.username if tracker.usuario else 'Sin asignar',
                'created_at': tracker.created_at,
                'updated_at': tracker.updated_at,
            })

        # 4. Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(trackers_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Obtener trámite por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_tracker(request, pk):
    try:
        tracker = get_object_or_404(Preparacion, pk=pk, estado_modulo=2)

        data = {
            "id": tracker.id,
            "placa": tracker.placa,
            "tipo_vehiculo": tracker.tipo_vehiculo,
            "departamento": tracker.departamento_id,
            "municipio": tracker.municipio_id,
            "estado": tracker.estado,
            "estado_tracker": tracker.estado_tracker,
            "estado_detalle": tracker.estado_detalle,
            "fecha_recepcion_municipio": tracker.fecha_recepcion_municipio,
            "hace_dias": tracker.hace_dias,
            "proveedor": tracker.proveedor_id,
            "codigo_encargado": tracker.codigo_encargado,
            "usuario": tracker.usuario.username if tracker.usuario else 'Sin asignar',
            "created_at": tracker.created_at,
            "updated_at": tracker.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving tracker: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar trámite
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_tracker(request, pk):
    try:
        tracker = get_object_or_404(Preparacion, pk=pk, estado_modulo=2)

        data = request.data

        # Actualizar campos
        tracker.placa = data.get('placa', tracker.placa).upper()
        tracker.tipo_vehiculo = data.get('tipo_vehiculo', tracker.tipo_vehiculo)
        tracker.estado = data.get('estado', tracker.estado)
        tracker.estado_detalle = data.get('estado_detalle', tracker.estado_detalle)
        tracker.estado_tracker = data.get('estado_tracker', tracker.estado_tracker)

        # Fecha de recepción
        if 'fecha_recepcion_municipio' in data:
            fecha_str = data.get('fecha_recepcion_municipio')
            if fecha_str:
                tracker.fecha_recepcion_municipio = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                tracker.fecha_recepcion_municipio = None

        # ForeignKeys
        if 'departamento' in data:
            tracker.departamento_id = data.get('departamento')
        if 'municipio' in data:
            tracker.municipio_id = data.get('municipio')
        if 'proveedor' in data:
            tracker.proveedor_id = data.get('proveedor')

        tracker.save()

        response_data = {
            "id": tracker.id,
            "placa": tracker.placa,
            "tipo_vehiculo": tracker.tipo_vehiculo,
            "estado": tracker.estado,
            "created_at": tracker.created_at.isoformat(),
        }

        # Notificar vía WebSocket
        tracker_data = {
            'id': tracker.id,
            'placa': tracker.placa,
            'tipo_vehiculo': tracker.tipo_vehiculo,
            'estado': tracker.estado,
            'estado_tracker': tracker.estado_tracker,
            'estado_detalle': tracker.estado_detalle,
            'fecha_recepcion_municipio': tracker.fecha_recepcion_municipio.isoformat() if tracker.fecha_recepcion_municipio else None,
            'hace_dias': tracker.hace_dias,
            'proveedor_id': tracker.proveedor_id,
            'codigo_encargado': tracker.codigo_encargado,
            'proveedor_nombre': tracker.proveedor.nombre if tracker.proveedor else None,
            'departamento': tracker.departamento_id,
            'municipio': tracker.municipio_id,
            'nombre_depto': tracker.departamento.departamento if tracker.departamento else None,
            'nombre_muni': tracker.municipio.municipio if tracker.municipio else None,
            'usuario': tracker.usuario.username if tracker.usuario else 'Sin asignar',
            'created_at': tracker.created_at.isoformat(),
            'updated_at': tracker.updated_at.isoformat(),
        }
        notify_tracker_updated(tracker_data)

        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error while updating tracker: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    except Exception as e:
        return Response(
            {"error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar trámite
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_tracker(request, pk):
    try:
        tracker = get_object_or_404(Preparacion, pk=pk, estado_modulo=2)

        # Guardar datos antes de eliminar para la notificación WebSocket
        tracker_id = tracker.id
        tracker_placa = tracker.placa

        tracker.delete()

        # Notificar vía WebSocket
        notify_tracker_deleted(tracker_id, tracker_placa)

        return Response(
            {"message": "Tracker deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error deleting tracker: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener historial del trámite
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_tracker_history(request, pk):
    try:
        # 1. Obtener el trámite principal
        tracker = get_object_or_404(Preparacion, pk=pk, estado_modulo=2)

        # 2. Obtener historial del trámite
        tracker_history = tracker.history.all().select_related('history_user')

        timeline = []

        # --- Procesar Historial del Tracker ---
        for record in tracker_history:
            cambios = []
            if record.prev_record:
                delta = record.diff_against(record.prev_record)
                for change in delta.changes:
                    cambios.append({
                        "campo": change.field,
                        "anterior": change.old,
                        "nuevo": change.new
                    })

            timeline.append({
                "fecha": record.history_date,
                "usuario": record.history_user.username if record.history_user else "Sistema",
                "entidad": "Trámite Tracker",
                "evento": record.get_history_type_display(),
                "descripcion": f"Cambio en datos del trámite {record.placa}",
                "detalles": cambios,
                "tipo": "tracker"
            })

        # 3. Ordenar toda la línea de tiempo por fecha descendente
        timeline.sort(key=lambda x: x['fecha'], reverse=True)

        return Response({
            "tracker_id": pk,
            "placa_actual": tracker.placa,
            "total_eventos": len(timeline),
            "trazabilidad_completa": timeline
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al generar trazabilidad: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Finalizar trámite (mover de Tracker a Finalizados)
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def finalizar_tracker(request, pk):
    """
    Finaliza un trámite en Tracker y lo transfiere automáticamente al módulo Finalizados.

    Flujo:
    1. Cambia estado_modulo de 2 (Tracker) a 3 (Finalizados)
    2. Actualiza estado_tracker a 'finalizado'
    3. Emite WebSocket a Tracker (eliminación)
    4. Emite WebSocket a Finalizados (creación)
    """
    try:
        with transaction.atomic():
            # 1. Obtener el trámite del módulo Tracker
            tracker = get_object_or_404(Preparacion, pk=pk, estado_modulo=2)

            # 2. Guardar datos del tracker antes de la transición (para notificaciones)
            tracker_data_before = {
                'id': tracker.id,
                'placa': tracker.placa,
            }

            # 3. Realizar la transición de módulo
            tracker.estado_modulo = 3  # Mover a Finalizados
            tracker.estado_tracker = 'finalizado'  # Marcar como finalizado
            tracker.estado = 'finalizado'  # Actualizar estado general

            # Opcionalmente actualizar estado_detalle
            if 'estado_detalle' in request.data:
                tracker.estado_detalle = request.data.get('estado_detalle', '')

            tracker.save()

            # 4. Construir datos completos para el módulo Finalizados (WebSocket)
            finalizado_data = {
                'id': tracker.id,
                'placa': tracker.placa,
                'tipo_vehiculo': tracker.tipo_vehiculo,
                'departamento': tracker.departamento_id,
                'municipio': tracker.municipio_id,
                'nombre_depto': tracker.departamento.departamento if tracker.departamento else None,
                'nombre_muni': tracker.municipio.municipio if tracker.municipio else None,
                'estado': tracker.estado,
                'estado_tracker': tracker.estado_tracker,
                'estado_detalle': tracker.estado_detalle,
                'fecha_recepcion_municipio': tracker.fecha_recepcion_municipio.isoformat() if tracker.fecha_recepcion_municipio else None,
                'hace_dias': tracker.hace_dias,
                'proveedor_id': tracker.proveedor_id,
                'codigo_encargado': tracker.codigo_encargado,
                'proveedor_nombre': tracker.proveedor.nombre if tracker.proveedor else None,
                'usuario': tracker.usuario.username if tracker.usuario else 'Sin asignar',
                'created_at': tracker.created_at.isoformat(),
                'updated_at': tracker.updated_at.isoformat(),
            }

            # 5. Emitir notificaciones WebSocket
            # 5.1. Notificar al módulo Tracker que el registro fue eliminado
            notify_tracker_deleted(tracker_data_before['id'], tracker_data_before['placa'])

            # 5.2. Notificar al módulo Finalizados que se creó un nuevo registro
            from finalizados.websocket.utils import notify_finalizado_created
            notify_finalizado_created(finalizado_data)

            return Response({
                "message": "Trámite finalizado exitosamente",
                "id": tracker.id,
                "placa": tracker.placa,
                "estado_modulo": tracker.estado_modulo,
                "estado_tracker": tracker.estado_tracker,
            }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Error al finalizar tracker: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error al finalizar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
