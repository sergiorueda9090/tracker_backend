from django.contrib import admin
from .models import Tracker


@admin.register(Tracker)
class TrackerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'placa', 'estado', 'tipo_vehiculo',
        'get_proveedor_codigo', 'usuario', 'hace_dias', 'created_at'
    )
    list_filter = ('estado', 'tipo_vehiculo', 'fecha_recepcion_municipio', 'proveedor')
    search_fields = ('placa', 'proveedor__codigo_encargado', 'proveedor__nombre', 'departamento__departamento', 'municipio__municipio')
    readonly_fields = ('created_at', 'updated_at', 'hace_dias', 'codigo_encargado')
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Información del Trámite', {
            'fields': ('usuario', 'placa', 'tipo_vehiculo', 'preparacion')
        }),
        ('Ubicación', {
            'fields': ('departamento', 'municipio', 'fecha_recepcion_municipio')
        }),
        ('Estado', {
            'fields': ('estado', 'estado_detalle')
        }),
        ('Proveedor', {
            'fields': ('proveedor', 'codigo_encargado'),
            'description': 'El código de encargado se obtiene automáticamente del proveedor seleccionado.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'hace_dias'),
            'classes': ('collapse',)
        }),
    )

    def get_proveedor_codigo(self, obj):
        """Muestra el código del proveedor en el listado"""
        return obj.codigo_encargado or '-'
    get_proveedor_codigo.short_description = 'Código Encargado'
    get_proveedor_codigo.admin_order_field = 'proveedor__codigo_encargado'
