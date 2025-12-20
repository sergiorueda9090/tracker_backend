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
        ('en_verificacion', 'En Verificación'),
        ('para_radicacion', 'Para Radicación'),
        ('en_novedad', 'En Novedad'),
        ('enviado_tracker', 'Enviado a Tracker'),
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

    # Estado del trámite
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='en_verificacion',
        help_text="Estado actual del trámite"
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
            models.Index(fields=['departamento', 'municipio'], name='idx_prep_ubicacion'),
            models.Index(fields=['created_at'], name='idx_prep_fecha'),
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
