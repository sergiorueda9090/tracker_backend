# preparacion/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError, transaction
from django.db.models import Q, Subquery, OuterRef
from datetime import datetime
import json

from preparacion.models import Preparacion, PreparacionArchivo
from user.api.permissions import RolePermission
from departamentos.models import Departamento
from municipios.models import Municipio
from preparacion.websocket.utils import notify_preparacion_created
import os


# ✅ Crear trámite en preparación
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_tramite(request):
    try:
        # Usamos atomic para asegurar que si algo falla, no se cree el trámite sin archivos
        with transaction.atomic():
            
            # 1. Extraer datos (manejo de QueryDict para multipart/form-data)
            data = request.data
            
            # Procesar lista_documentos si viene como string
            lista_docs = data.get('lista_documentos', [])
            if isinstance(lista_docs, str):
                try:
                    lista_docs = json.loads(lista_docs)
                except:
                    lista_docs = []

            # 2. Validaciones básicas
            placa = data.get('placa')
            tipo_vehiculo = data.get('tipo_vehiculo')
            departamento_id = data.get('departamento')
            municipio_id = data.get('municipio')

            if not all([placa, tipo_vehiculo, departamento_id, municipio_id]):
                return Response(
                    {"error": "Placa, tipo de vehículo, departamento y municipio son requeridos."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. Crear el trámite
            tramite = Preparacion.objects.create(
                usuario=request.user,
                placa=placa.upper(),
                tipo_vehiculo=tipo_vehiculo,
                departamento_id=departamento_id,
                municipio_id=municipio_id,
                estado=data.get('estado', 'en_verificacion'),
                paquete=data.get('paquete', ''),
                lista_documentos=lista_docs
            )

            # 4. Procesar archivos
            archivos_subidos = []
            if 'archivos' in request.FILES:
                files = request.FILES.getlist('archivos')
                tipos_permitidos = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']
                
                for f in files:
                    if f.content_type not in tipos_permitidos:
                        raise ValueError(f"Archivo {f.name} no permitido.")

                    # Crear el registro en la base de datos
                    archivo_obj = PreparacionArchivo.objects.create(
                        tramite=tramite,
                        archivo=f,
                        nombre_original=f.name,
                        tipo_archivo=f.content_type,
                        tamaño=f.size
                    )
                    
                    archivos_subidos.append({
                        "id": archivo_obj.id,
                        "nombre": archivo_obj.nombre_original,
                        "url": archivo_obj.archivo.url
                    })
            
            # 5. 🔥 Construir datos manualmente para WebSocket 🔥
            tramite_data = {
                'id': tramite.id,
                'placa': tramite.placa,
                'tipo_vehiculo': tramite.tipo_vehiculo,
                'estado': tramite.estado,
                'paquete': tramite.paquete,
                'lista_documentos': tramite.lista_documentos,
                'usuario': {
                    'id': tramite.usuario.id,
                    'nombre': tramite.usuario.get_full_name() if hasattr(tramite.usuario, 'get_full_name') else str(tramite.usuario),
                    'email': tramite.usuario.email
                },
                'departamento': {
                    'id': tramite.departamento.id,
                    'nombre': tramite.departamento.nombre
                } if tramite.departamento else None,
                'municipio': {
                    'id': tramite.municipio.id,
                    'nombre': tramite.municipio.nombre
                } if tramite.municipio else None,
                'fecha_creacion': tramite.fecha_creacion.isoformat() if hasattr(tramite, 'fecha_creacion') else None,
                'fecha_actualizacion': tramite.fecha_actualizacion.isoformat() if hasattr(tramite, 'fecha_actualizacion') else None,
                'archivos': archivos_subidos
            }
            
            # 6. 🔥 NOTIFICAR VÍA WEBSOCKET 🔥
            notify_preparacion_created(tramite_data)

            return Response({
                "id": tramite.id,
                "placa": tramite.placa,
                "estado": tramite.estado,
                "archivos": archivos_subidos
            }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Aquí es donde fallaba: a veces imprimir 'e' o 'data' causa el error de pickling
        print(f"Error detectado: {type(e).__name__}") 
        return Response(
            {"error": f"Error inesperado al procesar el trámite."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Listar trámites en preparación
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def list_tramites(request):
    try:
        # 1. Definir Subconsultas para obtener los nombres
        nombre_depto_subquery = Departamento.objects.filter(
            id_departamento=OuterRef('departamento')
        ).values('departamento')[:1]

        nombre_muni_subquery = Municipio.objects.filter(
            id_municipio=OuterRef('municipio')
        ).values('municipio')[:1]

        nombre_usuario_subquery = Preparacion.objects.filter(
            id=OuterRef('id')
        ).select_related('usuario').values('usuario__username')[:1]

        # 2. QuerySet Base con Annotation
        tramites = Preparacion.objects.select_related('usuario', 'departamento', 'municipio').annotate(
            nombre_depto=Subquery(nombre_depto_subquery),
            nombre_muni=Subquery(nombre_muni_subquery),
            nombre_usuario=Subquery(nombre_usuario_subquery)
        ).all()

        # --- Filtro de Buscador (Search) ---
        search_query = request.query_params.get('search', None)
        if search_query:
            tramites = tramites.filter(
                Q(placa__icontains=search_query) |
                Q(tipo_vehiculo__icontains=search_query) |
                Q(usuario__username__icontains=search_query) |
                Q(nombre_depto__icontains=search_query) |
                Q(nombre_muni__icontains=search_query)
            )

        # --- Filtros de Estado ---
        estado_filter = request.query_params.get('estado', None)
        if estado_filter:
            tramites = tramites.filter(estado=estado_filter)

        # --- Filtro de Tipo de Vehículo ---
        tipo_vehiculo_filter = request.query_params.get('tipo_vehiculo', None)
        if tipo_vehiculo_filter:
            tramites = tramites.filter(tipo_vehiculo=tipo_vehiculo_filter)

        # --- Filtros de Departamento y Municipio ---
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            tramites = tramites.filter(departamento=departamento_filter)

        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            tramites = tramites.filter(municipio=municipio_filter)

        # --- Filtros de Fecha ---
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

        # 3. Selección de campos (Values)
        tramites_data = []
        for tramite in tramites.order_by('-created_at'):
            # Obtener archivos del trámite
            archivos = tramite.archivos.all().values(
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

            tramites_data.append({
                'id': tramite.id,
                'placa': tramite.placa,
                'tipo_vehiculo': tramite.tipo_vehiculo,
                'departamento': tramite.departamento_id,
                'municipio': tramite.municipio_id,
                'nombre_depto': tramite.nombre_depto,
                'nombre_muni': tramite.nombre_muni,
                'estado': tramite.estado,
                'paquete': tramite.paquete,
                'lista_documentos': tramite.lista_documentos,
                'usuario': tramite.usuario.username if tramite.usuario else 'Sin asignar',
                'documentos_completos': tramite.documentos_completos,
                'documentos_completados': tramite.documentos_completados,
                'total_documentos': tramite.total_documentos,
                'created_at': tramite.created_at,
                'updated_at': tramite.updated_at,
                'archivos': archivos_list,
                'total_archivos': len(archivos_list)
            })

        # 4. Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(tramites_data, request)
        return paginator.get_paginated_response(paginated_queryset)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Obtener trámite por ID
@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_tramite(request, pk):
    try:
        tramite = get_object_or_404(Preparacion, pk=pk)

        # Obtener archivos del trámite
        archivos = tramite.archivos.all().values(
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

        data = {
            "id": tramite.id,
            "placa": tramite.placa,
            "tipo_vehiculo": tramite.tipo_vehiculo,
            "departamento": tramite.departamento_id,
            "municipio": tramite.municipio_id,
            "estado": tramite.estado,
            "paquete": tramite.paquete,
            "lista_documentos": tramite.lista_documentos,
            "usuario": tramite.usuario.username if tramite.usuario else 'Sin asignar',
            "created_at": tramite.created_at,
            "updated_at": tramite.updated_at,
            "archivos": archivos_list
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {"error": f"Error retrieving tramite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Actualizar trámite
@api_view(['PUT'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def update_tramite(request, pk):
    try:
        tramite = get_object_or_404(Preparacion, pk=pk)

        if request.content_type == 'application/json':
            data = request.data
        else:
            data = request.data.copy()

            if 'lista_documentos' in data and isinstance(data['lista_documentos'], str):
                try:
                    data['lista_documentos'] = json.loads(data['lista_documentos'])
                except json.JSONDecodeError:
                    data['lista_documentos'] = []

        tramite.placa = data.get('placa', tramite.placa).upper()
        tramite.tipo_vehiculo = data.get('tipo_vehiculo', tramite.tipo_vehiculo)
        tramite.estado = data.get('estado', tramite.estado)
        tramite.paquete = data.get('paquete', tramite.paquete)
        tramite.lista_documentos = data.get('lista_documentos', tramite.lista_documentos)

        if 'departamento' in data:
            tramite.departamento_id = data.get('departamento')
        if 'municipio' in data:
            tramite.municipio_id = data.get('municipio')

        tramite.save()

        # Procesar archivos subidos (agregar nuevos archivos)
        archivos_subidos = []
        if request.FILES:
            archivos = request.FILES.getlist('archivos')

            # Tipos de archivo permitidos
            tipos_permitidos = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg']

            for archivo in archivos:
                # Validar tipo de archivo
                if archivo.content_type not in tipos_permitidos:
                    return Response(
                        {"error": f"Tipo de archivo no permitido: {archivo.name}. Solo se permiten PDF, PNG y JPG."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Validar extensión del archivo
                extension = os.path.splitext(archivo.name)[1].lower()
                extensiones_permitidas = ['.pdf', '.png', '.jpg', '.jpeg']
                if extension not in extensiones_permitidas:
                    return Response(
                        {"error": f"Extensión de archivo no permitida: {archivo.name}. Solo se permiten .pdf, .png, .jpg"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Crear registro de archivo
                archivo_obj = PreparacionArchivo.objects.create(
                    tramite=tramite,
                    archivo=archivo,
                    nombre_original=archivo.name,
                    tipo_archivo=archivo.content_type,
                    tamaño=archivo.size
                )

                archivos_subidos.append({
                    "id": archivo_obj.id,
                    "nombre": archivo_obj.nombre_original,
                    "tipo": archivo_obj.tipo_archivo,
                    "tamaño": archivo_obj.tamaño,
                    "url": archivo_obj.archivo.url,
                    "created_at": archivo_obj.created_at
                })

        # Obtener todos los archivos del trámite
        todos_archivos = tramite.archivos.all().values(
            'id', 'nombre_original', 'tipo_archivo', 'tamaño', 'archivo', 'created_at'
        )
        archivos_list = [{
            "id": arch['id'],
            "nombre": arch['nombre_original'],
            "tipo": arch['tipo_archivo'],
            "tamaño": arch['tamaño'],
            "url": arch['archivo'],
            "created_at": arch['created_at']
        } for arch in todos_archivos]

        response_data = {
            "id": tramite.id,
            "placa": tramite.placa,
            "tipo_vehiculo": tramite.tipo_vehiculo,
            "estado": tramite.estado,
            "created_at": tramite.created_at,
            "archivos": archivos_list
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except DatabaseError as e:
        return Response(
            {"error": f"Database error while updating tramite: {str(e)}"},
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
def delete_tramite(request, pk):
    try:
        tramite = get_object_or_404(Preparacion, pk=pk)
        tramite.delete()
        return Response(
            {"message": "Tramite deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error deleting tramite: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Eliminar archivo individual
@api_view(['DELETE'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def delete_archivo(request, archivo_id):
    try:
        archivo = get_object_or_404(PreparacionArchivo, pk=archivo_id)

        # Eliminar el archivo físico del sistema
        if archivo.archivo:
            if os.path.exists(archivo.archivo.path):
                os.remove(archivo.archivo.path)

        # Eliminar el registro de la base de datos
        archivo.delete()

        return Response(
            {"message": "Archivo eliminado exitosamente"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Error al eliminar archivo: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def get_tramite_history(request, pk):
    try:
        # 1. Obtener el trámite principal
        tramite = get_object_or_404(Preparacion, pk=pk)
        
        # 2. Obtener historial del trámite (Tabla Preparacion)
        preparacion_history = tramite.history.all().select_related('history_user')
        
        # 3. Obtener historial de todos los archivos asociados a este trámite
        # Filtramos en la tabla de historia por el tramite_id
        archivos_history = PreparacionArchivo.history.filter(tramite_id=pk).select_related('history_user')

        timeline = []

        # --- Procesar Historial de Preparación ---
        for record in preparacion_history:
            cambios = []
            if record.prev_record:
                delta = record.diff_against(record.prev_record)
                for change in delta.changes:
                    cambios.append({"campo": change.field, "anterior": change.old, "nuevo": change.new})
            
            timeline.append({
                "fecha": record.history_date,
                "usuario": record.history_user.username if record.history_user else "Sistema",
                "entidad": "Trámite",
                "evento": record.get_history_type_display(),
                "descripcion": f"Cambio en datos del trámite {record.placa}",
                "detalles": cambios,
                "tipo": "tramite"
            })

        # --- Procesar Historial de Archivos ---
        for arch_record in archivos_history:
            cambios_arch = []
            if arch_record.prev_record:
                delta = arch_record.diff_against(arch_record.prev_record)
                for change in delta.changes:
                    cambios_arch.append({"campo": change.field, "anterior": change.old, "nuevo": change.new})

            timeline.append({
                "fecha": arch_record.history_date,
                "usuario": arch_record.history_user.username if arch_record.history_user else "Sistema",
                "entidad": "Archivo",
                "evento": arch_record.get_history_type_display(),
                "descripcion": f"Archivo: {arch_record.nombre_original}",
                "detalles": cambios_arch,
                "tipo": "archivo"
            })

        # 4. Ordenar toda la línea de tiempo por fecha descendente (lo más nuevo primero)
        timeline.sort(key=lambda x: x['fecha'], reverse=True)

        return Response({
            "tramite_id": pk,
            "placa_actual": tramite.placa,
            "total_eventos": len(timeline),
            "trazabilidad_completa": timeline
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": f"Error al generar trazabilidad: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )