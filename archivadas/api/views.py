# archivada/api/views.py
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
from archivadas.websocket.utils import (
    notify_archivada_created,
    notify_archivada_updated,
    notify_archivada_deleted
)


# ✅ Crear trámite en archivada
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_archivada(request):
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

            # 4. Crear el trámite (usando modelo Preparacion con estado_modulo=0)
            archivada = Preparacion.objects.create(
                usuario=request.user,
                placa=placa.upper(),
                tipo_vehiculo=tipo_vehiculo,
                departamento_id=departamento_id,
                municipio_id=municipio_id,
                estado=data.get('estado', 'en_radicacion'),  # Minúsculas
                estado_detalle=data.get('estado_detalle', ''),
                fecha_recepcion_municipio=fecha_recepcion,
                proveedor_id=proveedor_id,
                estado_modulo=0,  # CRÍTICO: Marca como módulo archivada
                paquete=data.get('paquete', ''),
                lista_documentos=data.get('lista_documentos', [])
            )

            # 5. Construir datos para WebSocket
            archivada_data = {
                'id': archivada.id,
                'placa': archivada.placa,
                'tipo_vehiculo': archivada.tipo_vehiculo,
                'departamento': archivada.departamento_id,
                'municipio': archivada.municipio_id,
                'nombre_depto': archivada.departamento.departamento if archivada.departamento else None,
                'nombre_muni': archivada.municipio.municipio if archivada.municipio else None,
                'estado': archivada.estado,
                'estado_detalle': archivada.estado_detalle,
                'fecha_recepcion_municipio': archivada.fecha_recepcion_municipio.isoformat() if archivada.fecha_recepcion_municipio else None,
                'hace_dias': archivada.hace_dias,
                'proveedor_id': archivada.proveedor_id,
                'codigo_encargado': archivada.codigo_encargado,
                'proveedor_nombre': archivada.proveedor.nombre if archivada.proveedor else None,
                'usuario': archivada.usuario.username if archivada.usuario else 'Sin asignar',
                'created_at': archivada.created_at.isoformat(),
                'updated_at': archivada.updated_at.isoformat(),
            }

            # 6. Notificar vía WebSocket
            notify_archivada_created(archivada_data)

            return Response({
                "id": archivada.id,
                "placa": archivada.placa,
                "estado": archivada.estado,
            }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        print(f"❌ Error completo al crear archivada: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error inesperado al procesar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar trámites en archivada
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_archivadas(request):
    try:
        # 1. Definir Subconsultas para obtener los nombres
        nombre_depto_subquery = Departamento.objects.filter(
            id_departamento=OuterRef('departamento')
        ).values('departamento')[:1]

        nombre_muni_subquery = Municipio.objects.filter(
            id_municipio=OuterRef('municipio')
        ).values('municipio')[:1]

        # 2. QuerySet Base con Annotation (filtrado por estado_modulo=0 para archivada)
        archivadas = Preparacion.objects.select_related(
            'usuario', 'departamento', 'municipio', 'proveedor'
        ).annotate(
            nombre_depto=Subquery(nombre_depto_subquery),
            nombre_muni=Subquery(nombre_muni_subquery)
        ).filter(estado_modulo=0)  # CRÍTICO: Solo registros del módulo archivada

        # --- Filtros ---
        # Filtro de búsqueda general
        search_query = request.query_params.get('search', None)
        if search_query:
            archivadas = archivadas.filter(
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
            archivadas = archivadas.filter(estado=estado_filter)

        # Filtro de tipo de vehículo
        tipo_vehiculo_filter = request.query_params.get('tipo_vehiculo', None)
        if tipo_vehiculo_filter:
            archivadas = archivadas.filter(tipo_vehiculo=tipo_vehiculo_filter)

        # Filtro de proveedor
        proveedor_filter = request.query_params.get('proveedor', None)
        if proveedor_filter:
            archivadas = archivadas.filter(proveedor_id=proveedor_filter)

        # Filtro de departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            archivadas = archivadas.filter(departamento_id=departamento_filter)

        # Filtro de municipio
        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            archivadas = archivadas.filter(municipio_id=municipio_filter)

        # Filtros de fecha de recepción
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            archivadas = archivadas.filter(fecha_recepcion_municipio__gte=start_date)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            archivadas = archivadas.filter(fecha_recepcion_municipio__lte=end_date)

        # 3. Construir datos
        archivadas_data = []
        for archivada in archivadas.order_by('-created_at'):

            # Obtener archivos del trámite
            archivos = archivada.archivos.all().values(
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

            archivadas_data.append({
                'id': archivada.id,
                'placa': archivada.placa,
                'archivos': archivos_list,
                'total_archivos': len(archivos_list),
                'tipo_vehiculo': archivada.tipo_vehiculo,
                'departamento': archivada.departamento_id,
                'municipio': archivada.municipio_id,
                'nombre_depto': archivada.nombre_depto,
                'nombre_muni': archivada.nombre_muni,
                'estado': archivada.estado,
                'estado_detalle': archivada.estado_detalle,
                'fecha_recepcion_municipio': archivada.fecha_recepcion_municipio,
                'hace_dias': archivada.hace_dias,
                'proveedor_id': archivada.proveedor_id,
                'codigo_encargado': archivada.codigo_encargado,
                'proveedor_nombre': archivada.proveedor.nombre if archivada.proveedor else None,
                'usuario': archivada.usuario.username if archivada.usuario else 'Sin asignar',
                'created_at': archivada.created_at,
                'updated_at': archivada.updated_at,
            })

        # 4. Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(archivadas_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Obtener trámite por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_archivada(request, pk):
    try:
        archivada = get_object_or_404(Preparacion, pk=pk, estado_modulo=0)

        data = {
            "id": archivada.id,
            "placa": archivada.placa,
            "tipo_vehiculo": archivada.tipo_vehiculo,
            "departamento": archivada.departamento_id,
            "municipio": archivada.municipio_id,
            "estado": archivada.estado,
            "estado_detalle": archivada.estado_detalle,
            "fecha_recepcion_municipio": archivada.fecha_recepcion_municipio,
            "hace_dias": archivada.hace_dias,
            "proveedor": archivada.proveedor_id,
            "codigo_encargado": archivada.codigo_encargado,
            "usuario": archivada.usuario.username if archivada.usuario else 'Sin asignar',
            "created_at": archivada.created_at,
            "updated_at": archivada.updated_at,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving archivada: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar trámite
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_archivada(request, pk):
    try:
        archivada = get_object_or_404(Preparacion, pk=pk, estado_modulo=0)

        data = request.data

        # Actualizar campos
        archivada.placa = data.get('placa', archivada.placa).upper()
        archivada.tipo_vehiculo = data.get('tipo_vehiculo', archivada.tipo_vehiculo)
        archivada.estado = data.get('estado', archivada.estado)
        archivada.estado_detalle = data.get('estado_detalle', archivada.estado_detalle)

        # Fecha de recepción
        if 'fecha_recepcion_municipio' in data:
            fecha_str = data.get('fecha_recepcion_municipio')
            if fecha_str:
                archivada.fecha_recepcion_municipio = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            else:
                archivada.fecha_recepcion_municipio = None

        # ForeignKeys
        if 'departamento' in data:
            archivada.departamento_id = data.get('departamento')
        if 'municipio' in data:
            archivada.municipio_id = data.get('municipio')
        if 'proveedor' in data:
            archivada.proveedor_id = data.get('proveedor')

        archivada.save()

        response_data = {
            "id": archivada.id,
            "placa": archivada.placa,
            "tipo_vehiculo": archivada.tipo_vehiculo,
            "estado": archivada.estado,
            "created_at": archivada.created_at.isoformat(),
        }

        # Notificar vía WebSocket
        archivada_data = {
            'id': archivada.id,
            'placa': archivada.placa,
            'tipo_vehiculo': archivada.tipo_vehiculo,
            'estado': archivada.estado,
            'estado_detalle': archivada.estado_detalle,
            'fecha_recepcion_municipio': archivada.fecha_recepcion_municipio.isoformat() if archivada.fecha_recepcion_municipio else None,
            'hace_dias': archivada.hace_dias,
            'proveedor_id': archivada.proveedor_id,
            'codigo_encargado': archivada.codigo_encargado,
            'proveedor_nombre': archivada.proveedor.nombre if archivada.proveedor else None,
            'departamento': archivada.departamento_id,
            'municipio': archivada.municipio_id,
            'nombre_depto': archivada.departamento.departamento if archivada.departamento else None,
            'nombre_muni': archivada.municipio.municipio if archivada.municipio else None,
            'usuario': archivada.usuario.username if archivada.usuario else 'Sin asignar',
            'created_at': archivada.created_at.isoformat(),
            'updated_at': archivada.updated_at.isoformat(),
        }
        notify_archivada_updated(archivada_data)

        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error while updating archivada: {str(e)}"},
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
def delete_archivada(request, pk):
    try:
        archivada = get_object_or_404(Preparacion, pk=pk, estado_modulo=0)

        # Guardar datos antes de eliminar para la notificación WebSocket
        archivada_id = archivada.id
        archivada_placa = archivada.placa

        archivada.delete()

        # Notificar vía WebSocket
        notify_archivada_deleted(archivada_id, archivada_placa)

        return Response(
            {"message": "archivada deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error deleting archivada: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener historial del trámite
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_archivada_history(request, pk):
    try:
        # 1. Obtener el trámite principal
        archivada = get_object_or_404(Preparacion, pk=pk, estado_modulo=0)

        # 2. Obtener historial del trámite
        archivada_history = archivada.history.all().select_related('history_user')

        timeline = []

        # --- Procesar Historial del archivada ---
        for record in archivada_history:
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
                "entidad": "Trámite archivada",
                "evento": record.get_history_type_display(),
                "descripcion": f"Cambio en datos del trámite {record.placa}",
                "detalles": cambios,
                "tipo": "archivada"
            })

        # 3. Ordenar toda la línea de tiempo por fecha descendente
        timeline.sort(key=lambda x: x['fecha'], reverse=True)

        return Response({
            "archivada_id": pk,
            "placa_actual": archivada.placa,
            "total_eventos": len(timeline),
            "trazabilidad_completa": timeline
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al generar trazabilidad: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Finalizar trámite (mover de archivada a Finalizados)
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def finalizar_archivada(request, pk):
    """
    Finaliza un trámite en archivada y lo transfiere automáticamente al módulo Finalizados.

    Flujo:
    1. Cambia estado_modulo de 0 (archivada) a 3 (Finalizados)
    2. Actualiza estado a 'finalizado'
    3. Emite WebSocket a archivada (eliminación)
    4. Emite WebSocket a Finalizados (creación)
    """
    try:
        with transaction.atomic():
            # 1. Obtener el trámite del módulo archivada
            archivada = get_object_or_404(Preparacion, pk=pk, estado_modulo=0)

            # 2. Guardar datos del archivada antes de la transición (para notificaciones)
            archivada_data_before = {
                'id': archivada.id,
                'placa': archivada.placa,
            }

            # 3. Realizar la transición de módulo
            archivada.estado_modulo = 3  # Mover a Finalizados
            archivada.estado = 'finalizado'  # Actualizar estado general

            # Opcionalmente actualizar estado_detalle
            if 'estado_detalle' in request.data:
                archivada.estado_detalle = request.data.get('estado_detalle', '')

            archivada.save()

            # 4. Construir datos completos para el módulo Finalizados (WebSocket)
            finalizado_data = {
                'id': archivada.id,
                'placa': archivada.placa,
                'tipo_vehiculo': archivada.tipo_vehiculo,
                'departamento': archivada.departamento_id,
                'municipio': archivada.municipio_id,
                'nombre_depto': archivada.departamento.departamento if archivada.departamento else None,
                'nombre_muni': archivada.municipio.municipio if archivada.municipio else None,
                'estado': archivada.estado,
                'estado_detalle': archivada.estado_detalle,
                'fecha_recepcion_municipio': archivada.fecha_recepcion_municipio.isoformat() if archivada.fecha_recepcion_municipio else None,
                'hace_dias': archivada.hace_dias,
                'proveedor_id': archivada.proveedor_id,
                'codigo_encargado': archivada.codigo_encargado,
                'proveedor_nombre': archivada.proveedor.nombre if archivada.proveedor else None,
                'usuario': archivada.usuario.username if archivada.usuario else 'Sin asignar',
                'created_at': archivada.created_at.isoformat(),
                'updated_at': archivada.updated_at.isoformat(),
            }

            # 5. Emitir notificaciones WebSocket
            # 5.1. Notificar al módulo archivada que el registro fue eliminado
            notify_archivada_deleted(archivada_data_before['id'], archivada_data_before['placa'])

            # 5.2. Notificar al módulo Finalizados que se creó un nuevo registro
            from finalizados.websocket.utils import notify_finalizado_created
            notify_finalizado_created(finalizado_data)

            return Response({
                "message": "Trámite finalizado exitosamente",
                "id": archivada.id,
                "placa": archivada.placa,
                "estado_modulo": archivada.estado_modulo,
            }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"❌ Error al finalizar archivada: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"Error al finalizar el trámite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
