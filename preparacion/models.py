from django.db import models
from user.models import User
from departamentos.models import Departamento
from municipios.models import Municipio
from simple_history.models import HistoricalRecords

# Create your models here.

class Preparacion(models.Model):
    """
    Modelo para gestionar trámites en preparación
    """

    # Opciones de estado
    ESTADO_CHOICES = [
        # Estados de Preparación
        ('en_verificacion', 'En Verificación'),
        ('para_radicacion', 'Para Radicación'),
        ('en_novedad', 'En Novedad'),
        ('enviado_tracker', 'Enviado a Tracker'),
        # Estados de Tracker (cuando estado_modulo=2)
        ('en_radicacion', 'En Radicación'),
        ('con_novedad', 'Con Novedad'),
        ('finalizado', 'Finalizado'),
    ]

    ESTADO_TRACKER = [
        ('sin_tracker', 'Sin Tracker'),
        ('en_radicacion', 'En Radicación'),
        ('con_novedad', 'Con Novedad'),
        ('finalizado', 'Finalizado'),
    ]

    # Opciones de tipo de vehículo
    TIPO_VEHICULO_CHOICES = [
        ('Automóvil', 'Automóvil'),
        ('Motocicleta', 'Motocicleta'),
        ('Camioneta', 'Camioneta'),
        ('Camión', 'Camión'),
        ('Bus', 'Bus'),
        ('Taxi', 'Taxi'),
        ('Otro', 'Otro'),
    ]

    # Usuario que creó el registro
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='tramites_preparacion',
        db_column='usuario_id',
        null=True,
        blank=True
    )

    # Información del vehículo
    placa = models.CharField(
        max_length=10,
        help_text="Placa del vehículo"
    )

    tipo_vehiculo = models.CharField(
        max_length=20,
        choices=TIPO_VEHICULO_CHOICES,
        help_text="Tipo de vehículo"
    )

    # Ubicación
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='tramites_preparacion',
        db_column='departamento_id',
        help_text="Departamento del trámite"
    )

    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='tramites_preparacion',
        db_column='municipio_id',
        help_text="Municipio del trámite"
    )

    # Proveedor (usado en módulo Tracker)
    proveedor = models.ForeignKey(
        'proveedores.Proveedor',
        on_delete=models.PROTECT,
        related_name='tramites_preparacion',
        db_column='proveedor_id',
        null=True,
        blank=True,
        help_text="Proveedor encargado del trámite (usado en módulo Tracker)"
    )

    # Estado del trámite
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='en_verificacion',
        help_text="Estado actual del trámite"
    )

    # Descripción detallada del estado (usado en módulo Tracker)
    estado_detalle = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del estado (alimentado por Proveedores en Tracker)"
    )

    # Fecha de recepción en municipio (usado en módulo Tracker)
    fecha_recepcion_municipio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de recepción en municipio (usado en módulo Tracker)"
    )

    # Estado del Modulo.
    """
        1. En preparcion
        2. En Tracker
        3. En Finalizados
        0. Archivados
    """
    estado_modulo = models.IntegerField(
        default=1,
        help_text="Estado del módulo: 1-En preparación, 2-En Tracker, 3-En Finalizados, 0-Archivados"
    )

    # Estado específico para módulo Tracker
    estado_tracker = models.CharField(
        max_length=20,
        choices=ESTADO_TRACKER,
        default='sin_tracker',
        help_text="Estado actual del trámite en módulo Tracker"
    )
    
    # Carpeta/paquete de archivos
    paquete = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ruta o nombre de la carpeta de archivos"
    )

    # Lista de chequeo de documentos (JSON)
    lista_documentos = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de documentos requeridos con su estado de completado"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización"
    )

    history = HistoricalRecords(
        table_name='history_preparacion',
        verbose_name='Historial de Preparación',
        related_name='historico'
    )

    class Meta:
        db_table = "preparacion"
        verbose_name = "Trámite en Preparación"
        verbose_name_plural = "Trámites en Preparación"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['placa'], name='idx_prep_placa'),
            models.Index(fields=['estado'], name='idx_prep_estado'),
            models.Index(fields=['estado_modulo'], name='idx_prep_estado_modulo'),
            models.Index(fields=['departamento', 'municipio'], name='idx_prep_ubicacion'),
            models.Index(fields=['created_at'], name='idx_prep_fecha'),
            models.Index(fields=['proveedor'], name='idx_prep_proveedor'),
            models.Index(fields=['fecha_recepcion_municipio'], name='idx_prep_fecha_recep'),
        ]

    def __str__(self):
        return f"{self.placa} - {self.get_estado_display()}"

    @property
    def documentos_completos(self):
        """Retorna True si todos los documentos están completados"""
        if not self.lista_documentos:
            return False
        return all(doc.get('completado', False) for doc in self.lista_documentos)

    @property
    def documentos_completados(self):
        """Retorna el número de documentos completados"""
        if not self.lista_documentos:
            return 0
        return sum(1 for doc in self.lista_documentos if doc.get('completado', False))

    @property
    def total_documentos(self):
        """Retorna el total de documentos en la lista"""
        if not self.lista_documentos:
            return 0
        return len(self.lista_documentos)

    @property
    def hace_dias(self):
        """
        Calcula días desde fecha_recepcion_municipio (solo para módulo Tracker).
        Retorna None si no hay fecha_recepcion_municipio.
        """
        if not self.fecha_recepcion_municipio:
            return None
        from django.utils import timezone
        hoy = timezone.now().date()
        return (hoy - self.fecha_recepcion_municipio).days

    @property
    def codigo_encargado(self):
        """Retorna código del proveedor (solo para módulo Tracker)"""
        return self.proveedor.codigo_encargado if self.proveedor else None


class PreparacionArchivo(models.Model):
    """
    Modelo para gestionar archivos asociados a un trámite de preparación
    """

    tramite = models.ForeignKey(
        Preparacion,
        on_delete=models.CASCADE,
        related_name='archivos',
        help_text="Trámite al que pertenece este archivo"
    )

    archivo = models.FileField(
        upload_to='preparacion/%Y/%m/%d/',
        help_text="Archivo PDF o imagen (PNG, JPG)"
    )

    nombre_original = models.CharField(
        max_length=255,
        help_text="Nombre original del archivo"
    )

    tipo_archivo = models.CharField(
        max_length=50,
        help_text="Tipo MIME del archivo (application/pdf, image/png, etc.)"
    )

    tamaño = models.IntegerField(
        help_text="Tamaño del archivo en bytes"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de carga"
    )

    history = HistoricalRecords(
        table_name='history_preparacion_archivos',
        verbose_name='Historial de Archivo',
        related_name='historico'
    )
    class Meta:
        db_table = "preparacion_archivos"
        verbose_name = "Archivo de Trámite"
        verbose_name_plural = "Archivos de Trámites"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['tramite'], name='idx_prep_arch_tramite'),
        ]

    def __str__(self):
        return f"{self.nombre_original} - {self.tramite.placa}"
