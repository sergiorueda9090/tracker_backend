# finalizado/api/views.py
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
from finalizados.websocket.utils import (
    notify_finalizado_created,
    notify_finalizado_updated,
    notify_finalizado_deleted
)


# ✅ Crear trámite en finalizado
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_finalizado(request):
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

            # 4. Crear el trámite (usando modelo Preparacion con estado_modulo=3)
            finalizado = Preparacion.objects.create(
                usuario=request.user,
                placa=placa.upper(),
                tipo_vehiculo=tipo_vehiculo,
                departamento_id=departamento_id,
                municipio_id=municipio_id,
                estado=data.get('estado', 'finalizado'),  # Estado finalizado por defecto
                estado_detalle=data.get('estado_detalle', ''),
                fecha_recepcion_municipio=fecha_recepcion,
                proveedor_id=proveedor_id,
                estado_modulo=3,  # CRÍTICO: Marca como módulo Finalizados
                estado_tracker=data.get('estado_tracker', 'finalizado'),
                paquete=data.get('paquete', ''),
                lista_documentos=data.get('lista_documentos', [])
            )

            # 5. Construir datos para WebSocket
            finalizado_data = {
                'id': finalizado.id,
                'placa': finalizado.placa,
                'tipo_vehiculo': finalizado.tipo_vehiculo,
                'departamento': finalizado.departamento_id,
                'municipio': finalizado.municipio_id,
                'nombre_depto': finalizado.departamento.departamento if finalizado.departamento else None,
                'nombre_muni': finalizado.municipio.municipio if finalizado.municipio else None,
                'estado': finalizado.estado,
                'estado_detalle': finalizado.estado_detalle,
                'fecha_recepcion_municipio': finalizado.fecha_recepcion_municipio.isoformat() if finalizado.fecha_recepcion_municipio else None,
                'hace_dias': finalizado.hace_dias,
                'proveedor_id': finalizado.proveedor_id,
                'codigo_encargado': finalizado.codigo_encargado,
                'proveedor_nombre': finalizado.proveedor.nombre if finalizado.proveedor else None,
                'usuario': finalizado.usuario.username if finalizado.usuario else 'Sin asignar',
                'created_at': finalizado.created_at.isoformat(),
                'updated_at': finalizado.updated_at.isoformat(),
            }

            # 6. Notificar vía WebSocket
            notify_finalizado_created(finalizado_data)

            return Response({
                "id": finalizado.id,
                "placa": finalizado.placa,
                "estado": finalizado.estado,
            }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"❌ Error completo al crear finalizado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error inesperado al procesar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar trámites en finalizado
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_finalizados(request):
    try:
        # 1. Definir Subconsultas para obtener los nombres
        nombre_depto_subquery = Departamento.objects.filter(
            id_departamento=OuterRef('departamento')
        ).values('departamento')[:1]

        nombre_muni_subquery = Municipio.objects.filter(
            id_municipio=OuterRef('municipio')
        ).values('municipio')[:1]

        # 2. QuerySet Base con Annotation (filtrado por estado_modulo=3 para finalizado)
        finalizados = Preparacion.objects.select_related(
            'usuario', 'departamento', 'municipio', 'proveedor'
        ).annotate(
            nombre_depto=Subquery(nombre_depto_subquery),
            nombre_muni=Subquery(nombre_muni_subquery)
        ).filter(estado_modulo=3)  # CRÍTICO: Solo registros del módulo Finalizados

        # --- Filtros ---
        # Filtro de búsqueda general
        search_query = request.query_params.get('search', None)
        if search_query:
            finalizados = finalizados.filter(
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
            finalizados = finalizados.filter(estado=estado_filter)

        # Filtro de tipo de vehículo
        tipo_vehiculo_filter = request.query_params.get('tipo_vehiculo', None)
        if tipo_vehiculo_filter:
            finalizados = finalizados.filter(tipo_vehiculo=tipo_vehiculo_filter)

        # Filtro de proveedor
        proveedor_filter = request.query_params.get('proveedor', None)
        if proveedor_filter:
            finalizados = finalizados.filter(proveedor_id=proveedor_filter)

        # Filtro de departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            finalizados = finalizados.filter(departamento_id=departamento_filter)

        # Filtro de municipio
        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            finalizados = finalizados.filter(municipio_id=municipio_filter)

        # Filtros de fecha de recepción
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            finalizados = finalizados.filter(fecha_recepcion_municipio__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            finalizados = finalizados.filter(fecha_recepcion_municipio__lte=end_date)

        # 3. Construir datos
        finalizados_data = []
        for finalizado in finalizados.order_by('-created_at'):

            # Obtener archivos del trámite
            archivos = finalizado.archivos.all().values(
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

            finalizados_data.append({
                'id': finalizado.id,
                'placa': finalizado.placa,
                'archivos': archivos_list,
                'total_archivos': len(archivos_list),
                'tipo_vehiculo': finalizado.tipo_vehiculo,
                'departamento': finalizado.departamento_id,
                'municipio': finalizado.municipio_id,
                'nombre_depto': finalizado.nombre_depto,
                'nombre_muni': finalizado.nombre_muni,
                'estado': finalizado.estado,
                'estado_detalle': finalizado.estado_detalle,
                'estado_tracker': finalizado.estado_tracker,
                'fecha_recepcion_municipio': finalizado.fecha_recepcion_municipio,
                'hace_dias': finalizado.hace_dias,
                'proveedor_id': finalizado.proveedor_id,
                'codigo_encargado': finalizado.codigo_encargado,
                'proveedor_nombre': finalizado.proveedor.nombre if finalizado.proveedor else None,
                'usuario': finalizado.usuario.username if finalizado.usuario else 'Sin asignar',
                'created_at': finalizado.created_at,
                'updated_at': finalizado.updated_at,
            })

        # 4. Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(finalizados_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Obtener trámite por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_finalizado(request, pk):
    try:
        finalizado = get_object_or_404(Preparacion, pk=pk, estado_modulo=3)

        data = {
            "id": finalizado.id,
            "placa": finalizado.placa,
            "tipo_vehiculo": finalizado.tipo_vehiculo,
            "departamento": finalizado.departamento_id,
            "municipio": finalizado.municipio_id,
            "estado": finalizado.estado,
            "estado_tracker": finalizado.estado_tracker,
            "estado_detalle": finalizado.estado_detalle,
            "fecha_recepcion_municipio": finalizado.fecha_recepcion_municipio,
            "hace_dias": finalizado.hace_dias,
            "proveedor": finalizado.proveedor_id,
            "codigo_encargado": finalizado.codigo_encargado,
            "usuario": finalizado.usuario.username if finalizado.usuario else 'Sin asignar',
            "created_at": finalizado.created_at,
            "updated_at": finalizado.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving finalizado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar trámite
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_finalizado(request, pk):
    try:
        finalizado = get_object_or_404(Preparacion, pk=pk, estado_modulo=3)

        data = request.data

        # Actualizar campos
        finalizado.placa = data.get('placa', finalizado.placa).upper()
        finalizado.tipo_vehiculo = data.get('tipo_vehiculo', finalizado.tipo_vehiculo)
        finalizado.estado = data.get('estado', finalizado.estado)
        finalizado.estado_detalle = data.get('estado_detalle', finalizado.estado_detalle)
        finalizado.estado_tracker = data.get('estado_tracker', finalizado.estado_tracker)

        # Fecha de recepción
        if 'fecha_recepcion_municipio' in data:
            fecha_str = data.get('fecha_recepcion_municipio')
            if fecha_str:
                finalizado.fecha_recepcion_municipio = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                finalizado.fecha_recepcion_municipio = None

        # ForeignKeys
        if 'departamento' in data:
            finalizado.departamento_id = data.get('departamento')
        if 'municipio' in data:
            finalizado.municipio_id = data.get('municipio')
        if 'proveedor' in data:
            finalizado.proveedor_id = data.get('proveedor')

        finalizado.save()

        response_data = {
            "id": finalizado.id,
            "placa": finalizado.placa,
            "tipo_vehiculo": finalizado.tipo_vehiculo,
            "estado": finalizado.estado,
            "created_at": finalizado.created_at.isoformat(),
        }

        # Notificar vía WebSocket
        finalizado_data = {
            'id': finalizado.id,
            'placa': finalizado.placa,
            'tipo_vehiculo': finalizado.tipo_vehiculo,
            'estado': finalizado.estado,
            'estado_tracker': finalizado.estado_tracker,
            'estado_detalle': finalizado.estado_detalle,
            'fecha_recepcion_municipio': finalizado.fecha_recepcion_municipio.isoformat() if finalizado.fecha_recepcion_municipio else None,
            'hace_dias': finalizado.hace_dias,
            'proveedor_id': finalizado.proveedor_id,
            'codigo_encargado': finalizado.codigo_encargado,
            'proveedor_nombre': finalizado.proveedor.nombre if finalizado.proveedor else None,
            'departamento': finalizado.departamento_id,
            'municipio': finalizado.municipio_id,
            'nombre_depto': finalizado.departamento.departamento if finalizado.departamento else None,
            'nombre_muni': finalizado.municipio.municipio if finalizado.municipio else None,
            'usuario': finalizado.usuario.username if finalizado.usuario else 'Sin asignar',
            'created_at': finalizado.created_at.isoformat(),
            'updated_at': finalizado.updated_at.isoformat(),
        }
        notify_finalizado_updated(finalizado_data)

        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error while updating finalizado: {str(e)}"},
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
def delete_finalizado(request, pk):
    try:
        finalizado = get_object_or_404(Preparacion, pk=pk, estado_modulo=3)

        # Guardar datos antes de eliminar para la notificación WebSocket
        finalizado_id = finalizado.id
        finalizado_placa = finalizado.placa

        finalizado.delete()

        # Notificar vía WebSocket
        notify_finalizado_deleted(finalizado_id, finalizado_placa)

        return Response(
            {"message": "finalizado deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error deleting finalizado: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener historial del trámite
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_finalizado_history(request, pk):
    try:
        # 1. Obtener el trámite principal
        finalizado = get_object_or_404(Preparacion, pk=pk, estado_modulo=3)

        # 2. Obtener historial del trámite
        finalizado_history = finalizado.history.all().select_related('history_user')

        timeline = []

        # --- Procesar Historial del finalizado ---
        for record in finalizado_history:
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
                "entidad": "Trámite finalizado",
                "evento": record.get_history_type_display(),
                "descripcion": f"Cambio en datos del trámite {record.placa}",
                "detalles": cambios,
                "tipo": "finalizado"
            })

        # 3. Ordenar toda la línea de tiempo por fecha descendente
        timeline.sort(key=lambda x: x['fecha'], reverse=True)

        return Response({
            "finalizado_id": pk,
            "placa_actual": finalizado.placa,
            "total_eventos": len(timeline),
            "trazabilidad_completa": timeline
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al generar trazabilidad: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Archivar trámite (mover de Finalizados a Archivadas)
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def archivar_finalizado(request, pk):
    """
    Archiva un trámite finalizado y lo transfiere automáticamente al módulo Archivadas.

    Flujo:
    1. Cambia estado_modulo de 3 (Finalizados) a 0 (Archivadas)
    2. Emite WebSocket a Finalizados (eliminación)
    3. Emite WebSocket a Archivadas (creación)
    """
    try:
        with transaction.atomic():
            # 1. Obtener el trámite del módulo Finalizados
            finalizado = get_object_or_404(Preparacion, pk=pk, estado_modulo=3)

            # 2. Guardar datos del finalizado antes de la transición (para notificaciones)
            finalizado_data_before = {
                'id': finalizado.id,
                'placa': finalizado.placa,
            }

            # 3. Realizar la transición de módulo
            finalizado.estado_modulo = 0  # Mover a Archivadas
            finalizado.save()

            # 4. Construir datos completos para el módulo Archivadas (WebSocket)
            archivada_data = {
                'id': finalizado.id,
                'placa': finalizado.placa,
                'tipo_vehiculo': finalizado.tipo_vehiculo,
                'departamento': finalizado.departamento_id,
                'municipio': finalizado.municipio_id,
                'nombre_depto': finalizado.departamento.departamento if finalizado.departamento else None,
                'nombre_muni': finalizado.municipio.municipio if finalizado.municipio else None,
                'estado': finalizado.estado,
                'estado_detalle': finalizado.estado_detalle,
                'fecha_recepcion_municipio': finalizado.fecha_recepcion_municipio.isoformat() if finalizado.fecha_recepcion_municipio else None,
                'hace_dias': finalizado.hace_dias,
                'proveedor_id': finalizado.proveedor_id,
                'codigo_encargado': finalizado.codigo_encargado,
                'proveedor_nombre': finalizado.proveedor.nombre if finalizado.proveedor else None,
                'usuario': finalizado.usuario.username if finalizado.usuario else 'Sin asignar',
                'created_at': finalizado.created_at.isoformat(),
                'updated_at': finalizado.updated_at.isoformat(),
            }

            # 5. Emitir notificaciones WebSocket
            # 5.1. Notificar al módulo Finalizados que el registro fue eliminado
            notify_finalizado_deleted(finalizado_data_before['id'], finalizado_data_before['placa'])

            # 5.2. Notificar al módulo Archivadas que se creó un nuevo registro
            from archivadas.websocket.utils import notify_archivada_created
            notify_archivada_created(archivada_data)

            return Response({
                "message": f"Trámite {finalizado.placa} archivado exitosamente",
                "id": finalizado.id,
                "placa": finalizado.placa,
                "estado_modulo": finalizado.estado_modulo,
            }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Error al archivar finalizado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error al archivar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
