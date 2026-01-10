from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(SimpleHistoryAdmin):
    list_display = ('nit', 'nombre', 'razon_social', 'departamento', 'ciudad', 'is_active', 'created_at')
    list_filter = ('is_active', 'departamento', 'created_at')
    search_fields = ('nit', 'nombre', 'razon_social')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'razon_social', 'nit')
        }),
        ('Ubicación', {
            'fields': ('departamento', 'ciudad')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
