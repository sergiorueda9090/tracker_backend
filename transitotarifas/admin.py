from django.contrib import admin
from .models import TransitoTarifa, TransitoTarifaTramite, TransitoTarifaGestor


class TransitoTarifaGestorInline(admin.TabularInline):
    model = TransitoTarifaGestor
    extra = 1
    fields = ('proveedor', 'servicio_gestor', 'servicio_empresa')


class TransitoTarifaTramiteInline(admin.TabularInline):
    model = TransitoTarifaTramite
    extra = 1
    fields = ('tramite', 'derechos_2026')


@admin.register(TransitoTarifa)
class TransitoTarifaAdmin(admin.ModelAdmin):
    list_display = ('id', 'departamento', 'municipio', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'departamento', 'created_at')
    search_fields = ('departamento__departamento', 'municipio__municipio')
    inlines = [TransitoTarifaTramiteInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TransitoTarifaTramite)
class TransitoTarifaTramiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'transito_tarifa', 'tramite', 'derechos_2026', 'created_at')
    list_filter = ('tramite', 'created_at')
    search_fields = ('tramite__nombre', 'transito_tarifa__departamento__departamento')
    inlines = [TransitoTarifaGestorInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TransitoTarifaGestor)
class TransitoTarifaGestorAdmin(admin.ModelAdmin):
    list_display = ('id', 'tramite_tarifa', 'proveedor', 'servicio_gestor', 'servicio_empresa', 'margen_ganancia', 'created_at')
    list_filter = ('proveedor', 'created_at')
    search_fields = ('proveedor__nombre', 'tramite_tarifa__tramite__nombre')
    readonly_fields = ('created_at', 'updated_at', 'margen_ganancia', 'porcentaje_margen')
