from django.contrib import admin
from .models import Liquidacion


@admin.register(Liquidacion)
class LiquidacionAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'placa',
        'tramite',
        'proveedor',
        'cliente',
        'derechos_tramite',
        'servicio_empresa',
        'servicio_gestor',
        'utilidad_display',
        'estado',
        'fecha_finalizado',
    ]
    list_filter = [
        'estado',
        'tramite',
        'proveedor',
        'departamento',
        'fecha_finalizado',
    ]
    search_fields = [
        'placa',
        'tramite__nombre',
        'proveedor__nombre',
        'proveedor__codigo_encargado',
        'cliente__nombre',
    ]
    readonly_fields = [
        'iva_servicio_display',
        'total_facturacion_display',
        'total_servicio_gestor_display',
        'utilidad_display',
        'es_rentable',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Información General', {
            'fields': ('preparacion', 'placa', 'tipo_vehiculo', 'tramite', 'estado')
        }),
        ('Ubicación', {
            'fields': ('departamento', 'municipio')
        }),
        ('Participantes', {
            'fields': ('proveedor', 'cliente')
        }),
        ('Facturación', {
            'fields': (
                'derechos_tramite',
                'servicio_empresa',
                'iva_servicio_display',
                'total_facturacion_display',
            )
        }),
        ('Servicio Gestor', {
            'fields': (
                'servicio_gestor',
                'transporte',
                'bonificacion',
                'anticipos',
                'total_servicio_gestor_display',
            )
        }),
        ('Utilidad', {
            'fields': ('utilidad_display', 'es_rentable')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Auditoría', {
            'fields': ('fecha_finalizado', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def iva_servicio_display(self, obj):
        return f"${obj.iva_servicio:,.2f}"
    iva_servicio_display.short_description = 'IVA (19%)'

    def total_facturacion_display(self, obj):
        return f"${obj.total_facturacion:,.2f}"
    total_facturacion_display.short_description = 'Total Facturación'

    def total_servicio_gestor_display(self, obj):
        return f"${obj.total_servicio_gestor:,.2f}"
    total_servicio_gestor_display.short_description = 'Total Servicio Gestor'

    def utilidad_display(self, obj):
        color = 'green' if obj.es_rentable else 'red'
        return f"${obj.utilidad:,.2f}"
    utilidad_display.short_description = 'Utilidad'
