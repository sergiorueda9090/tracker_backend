# transitotarifas/api/views.py
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db import DatabaseError, transaction
from django.db.models import Q
from datetime import datetime

from transitotarifas.models import TransitoTarifa, TransitoTarifaTramite, TransitoTarifaGestor
from tramites.models import Tramite
from proveedores.models import Proveedor
from departamentos.models import Departamento
from municipios.models import Municipio
from user.api.permissions import RolePermission


# ✅ Crear tránsito tarifa con estructura completa
@api_view(['POST'])
@permission_classes([IsAuthenticated, RolePermission(['admin'])])
def create_transito_tarifa(request):
    try:
        data = request.data

        departamento_id = data.get('departamento_id')
        municipio_id = data.get('municipio_id')
        tramites_data = data.get('tramites', [])

        # Validaciones básicas
        if not departamento_id:
            return Response(
                {"error": "El departamento es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not municipio_id:
            return Response(
                {"error": "El municipio es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not tramites_data or len(tramites_data) == 0:
            return Response(
                {"error": "Debe agregar al menos un trámite."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que existan el departamento y municipio
        try:
            departamento = Departamento.objects.get(pk=departamento_id)
        except Departamento.DoesNotExist:
            return Response(
                {"error": "El departamento especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            municipio = Municipio.objects.get(pk=municipio_id)
        except Municipio.DoesNotExist:
            return Response(
                {"error": "El municipio especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si ya existe esta combinación
        if TransitoTarifa.objects.filter(departamento=departamento, municipio=municipio).exists():
            return Response(
                {"error": "Ya existe una configuración para este departamento y municipio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Usar transacción para asegurar integridad
        with transaction.atomic():
            # Crear TransitoTarifa (nivel 1)
            transito_tarifa = TransitoTarifa.objects.create(
                departamento=departamento,
                municipio=municipio
            )

            # Crear TransitoTarifaTramite y TransitoTarifaGestor (niveles 2 y 3)
            for tramite_data in tramites_data:
                tramite_id = tramite_data.get('tramite_id')
                derechos_2026 = tramite_data.get('derechos_2026')
                gestores_data = tramite_data.get('gestores', [])

                # Validar trámite
                if not tramite_id:
                    raise ValueError("Cada trámite debe tener un tramite_id.")

                if not derechos_2026:
                    raise ValueError("Cada trámite debe tener derechos_2026.")

                if not gestores_data or len(gestores_data) == 0:
                    raise ValueError(f"El trámite debe tener al menos un gestor.")

                try:
                    tramite = Tramite.objects.get(pk=tramite_id)
                except Tramite.DoesNotExist:
                    raise ValueError(f"El trámite con ID {tramite_id} no existe.")

                # Crear TransitoTarifaTramite (nivel 2)
                tramite_tarifa = TransitoTarifaTramite.objects.create(
                    transito_tarifa=transito_tarifa,
                    tramite=tramite,
                    derechos_2026=derechos_2026
                )

                # Crear TransitoTarifaGestor (nivel 3)
                for gestor_data in gestores_data:
                    proveedor_id = gestor_data.get('proveedor_id')
                    servicio_gestor = gestor_data.get('servicio_gestor')
                    servicio_empresa = gestor_data.get('servicio_empresa')

                    # Validar gestor
                    if not proveedor_id:
                        raise ValueError("Cada gestor debe tener un proveedor_id.")

                    if not servicio_gestor:
                        raise ValueError("Cada gestor debe tener servicio_gestor.")

                    if not servicio_empresa:
                        raise ValueError("Cada gestor debe tener servicio_empresa.")

                    try:
                        proveedor = Proveedor.objects.get(pk=proveedor_id)
                    except Proveedor.DoesNotExist:
                        raise ValueError(f"El proveedor con ID {proveedor_id} no existe.")

                    TransitoTarifaGestor.objects.create(
                        tramite_tarifa=tramite_tarifa,
                        proveedor=proveedor,
                        servicio_gestor=servicio_gestor,
                        servicio_empresa=servicio_empresa
                    )

        # Retornar datos creados
        response_data = {
            "id": transito_tarifa.id,
            "departamento_id": transito_tarifa.departamento.id_departamento,
            "municipio_id": transito_tarifa.municipio.id_municipio,
            "is_active": transito_tarifa.is_active,
            "created_at": transito_tarifa.created_at,
            "updated_at": transito_tarifa.updated_at,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
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
        # QuerySet base
        transito_tarifas = TransitoTarifa.objects.select_related(
            'departamento', 'municipio'
        ).prefetch_related(
            'tramites__tramite',
            'tramites__gestores__proveedor'
        )

        # Filtro de búsqueda
        search_query = request.query_params.get('search', None)
        if search_query:
            transito_tarifas = transito_tarifas.filter(
                Q(departamento__departamento__icontains=search_query) |
                Q(municipio__municipio__icontains=search_query)
            )

        # Filtro por departamento
        departamento_filter = request.query_params.get('departamento', None)
        if departamento_filter:
            transito_tarifas = transito_tarifas.filter(departamento_id=departamento_filter)

        # Filtro por municipio
        municipio_filter = request.query_params.get('municipio', None)
        if municipio_filter:
            transito_tarifas = transito_tarifas.filter(municipio_id=municipio_filter)

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

        # Ordenar
        transito_tarifas = transito_tarifas.order_by('departamento__departamento', 'municipio__municipio')

        # Paginación
        page_size = int(request.query_params.get('page_size', 10))
        paginator = PageNumberPagination()
        paginator.page_size = page_size

        paginated_queryset = paginator.paginate_queryset(transito_tarifas, request)

        # Serializar datos
        results = []
        for tarifa in paginated_queryset:
            results.append({
                'id': tarifa.id,
                'departamento_id': tarifa.departamento.id_departamento,
                'departamento_nombre': tarifa.departamento.departamento,
                'municipio_id': tarifa.municipio.id_municipio,
                'municipio_nombre': tarifa.municipio.municipio,
                'is_active': tarifa.is_active,
                'created_at': tarifa.created_at,
                'updated_at': tarifa.updated_at,
                'total_tramites': tarifa.tramites.count(),
            })

        return paginator.get_paginated_response(results)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ✅ Obtener tránsito tarifa por ID con toda la estructura
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_transito_tarifa(request, pk):
    try:
        transito_tarifa = get_object_or_404(
            TransitoTarifa.objects.select_related('departamento', 'municipio')
            .prefetch_related('tramites__tramite', 'tramites__gestores__proveedor'),
            pk=pk
        )

        # Serializar estructura completa
        tramites_data = []
        for tramite_tarifa in transito_tarifa.tramites.all():
            gestores_data = []
            for gestor in tramite_tarifa.gestores.all():
                gestores_data.append({
                    'proveedor_id': gestor.proveedor.id,
                    'proveedor_nombre': gestor.proveedor.nombre,
                    'proveedor_codigo': gestor.proveedor.codigo_encargado,
                    'servicio_gestor': str(gestor.servicio_gestor),
                    'servicio_empresa': str(gestor.servicio_empresa),
                })

            tramites_data.append({
                'tramite_id': tramite_tarifa.tramite.id,
                'tramite_nombre': tramite_tarifa.tramite.nombre,
                'derechos_2026': str(tramite_tarifa.derechos_2026),
                'gestores': gestores_data,
            })

        data = {
            "id": transito_tarifa.id,
            "departamento_id": transito_tarifa.departamento.id_departamento,
            "departamento_nombre": transito_tarifa.departamento.departamento,
            "municipio_id": transito_tarifa.municipio.id_municipio,
            "municipio_nombre": transito_tarifa.municipio.municipio,
            "is_active": transito_tarifa.is_active,
            "created_at": transito_tarifa.created_at,
            "updated_at": transito_tarifa.updated_at,
            "tramites": tramites_data,
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

        departamento_id = data.get('departamento_id')
        municipio_id = data.get('municipio_id')
        tramites_data = data.get('tramites', [])

        # Validaciones
        if not departamento_id:
            return Response(
                {"error": "El departamento es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not municipio_id:
            return Response(
                {"error": "El municipio es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not tramites_data or len(tramites_data) == 0:
            return Response(
                {"error": "Debe agregar al menos un trámite."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que existan el departamento y municipio
        try:
            departamento = Departamento.objects.get(pk=departamento_id)
        except Departamento.DoesNotExist:
            return Response(
                {"error": "El departamento especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            municipio = Municipio.objects.get(pk=municipio_id)
        except Municipio.DoesNotExist:
            return Response(
                {"error": "El municipio especificado no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si ya existe otra configuración con esta combinación
        if TransitoTarifa.objects.filter(
            departamento=departamento,
            municipio=municipio
        ).exclude(pk=pk).exists():
            return Response(
                {"error": "Ya existe una configuración para este departamento y municipio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Usar transacción
        with transaction.atomic():
            # Actualizar departamento y municipio
            transito_tarifa.departamento = departamento
            transito_tarifa.municipio = municipio
            transito_tarifa.save()

            # Eliminar trámites y gestores anteriores (CASCADE elimina gestores automáticamente)
            transito_tarifa.tramites.all().delete()

            # Crear nuevos trámites y gestores
            for tramite_data in tramites_data:
                tramite_id = tramite_data.get('tramite_id')
                derechos_2026 = tramite_data.get('derechos_2026')
                gestores_data = tramite_data.get('gestores', [])

                # Validar trámite
                if not tramite_id:
                    raise ValueError("Cada trámite debe tener un tramite_id.")

                if not derechos_2026:
                    raise ValueError("Cada trámite debe tener derechos_2026.")

                if not gestores_data or len(gestores_data) == 0:
                    raise ValueError(f"El trámite debe tener al menos un gestor.")

                try:
                    tramite = Tramite.objects.get(pk=tramite_id)
                except Tramite.DoesNotExist:
                    raise ValueError(f"El trámite con ID {tramite_id} no existe.")

                # Crear TransitoTarifaTramite
                tramite_tarifa = TransitoTarifaTramite.objects.create(
                    transito_tarifa=transito_tarifa,
                    tramite=tramite,
                    derechos_2026=derechos_2026
                )

                # Crear TransitoTarifaGestor
                for gestor_data in gestores_data:
                    proveedor_id = gestor_data.get('proveedor_id')
                    servicio_gestor = gestor_data.get('servicio_gestor')
                    servicio_empresa = gestor_data.get('servicio_empresa')

                    # Validar gestor
                    if not proveedor_id:
                        raise ValueError("Cada gestor debe tener un proveedor_id.")

                    if not servicio_gestor:
                        raise ValueError("Cada gestor debe tener servicio_gestor.")

                    if not servicio_empresa:
                        raise ValueError("Cada gestor debe tener servicio_empresa.")

                    try:
                        proveedor = Proveedor.objects.get(pk=proveedor_id)
                    except Proveedor.DoesNotExist:
                        raise ValueError(f"El proveedor con ID {proveedor_id} no existe.")

                    TransitoTarifaGestor.objects.create(
                        tramite_tarifa=tramite_tarifa,
                        proveedor=proveedor,
                        servicio_gestor=servicio_gestor,
                        servicio_empresa=servicio_empresa
                    )

        # Retornar datos actualizados
        response_data = {
            "id": transito_tarifa.id,
            "departamento_id": transito_tarifa.departamento.id_departamento,
            "municipio_id": transito_tarifa.municipio.id_municipio,
            "is_active": transito_tarifa.is_active,
        }
        return Response(response_data, status=status.HTTP_200_OK)

    except ValueError as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except DatabaseError as e:
        return Response(
            {"error": f"Error de base de datos al actualizar: {str(e)}"},
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
            {"message": "Tránsito tarifa eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )
    except Exception as e:
        return Response(
            {"error": f"Error al eliminar tránsito tarifa: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
