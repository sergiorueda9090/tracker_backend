from django.db import models
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords

from proveedores.models import Proveedor
from departamentos.models import Departamento
from municipios.models import Municipio
from preparacion.models import Preparacion


class Tracker(models.Model):
    """
    Modelo para gestionar trámites en el sistema Tracker.

    Este modelo representa un trámite que ha pasado del módulo "En Preparación"
    al módulo "Tracker" para su seguimiento y radicación.

    Decisiones de diseño:
    - `codigo_encargado` se relaciona con el modelo Proveedor mediante FK porque
      Proveedor tiene un campo `codigo_encargado` único que sirve como identificador.
    - `paquete` se relaciona con Preparacion porque el trámite proviene del módulo
      "En preparación" y mantiene la trazabilidad completa.
    - `hace_dias` es una propiedad calculada, NO un campo en base de datos.
    """

    # Opciones de estado
    ESTADO_CHOICES = [
        ('EN_RADICACION', 'En Radicación'),
        ('CON_NOVEDAD', 'Con Novedad'),
        ('FINALIZADO', 'Finalizado'),
    ]

    # Opciones de tipo de vehículo (pueden agregarse más en el futuro)
    TIPO_VEHICULO_CHOICES = [
        ('AUTOMOVIL', 'Automóvil'),
        ('MOTOCICLETA', 'Motocicleta'),
        ('CAMIONETA', 'Camioneta'),
        ('CAMION', 'Camión'),
        ('BUS', 'Bus'),
        ('TAXI', 'Taxi'),
        ('OTRO', 'Otro'),
    ]

    # 1. ID - Automático (BigAutoField por defecto en Django 3.2+)

    # 2. Usuario que creó el registro
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='radicaciones_creadas',
        db_column='usuario_id',
        help_text="Usuario que creó el registro en el sistema",
        null=True,
        blank=True
    )

    # 3. Fecha de recepción en municipio (editable manualmente)
    fecha_recepcion_municipio = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que el trámite fue recibido en el municipio (editable manualmente)"
    )

    # 5. Estado del trámite
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='EN_RADICACION',
        help_text="Estado actual del trámite"
    )

    # 6. Descripción detallada del estado (opcional, alimentado por Proveedores)
    estado_detalle = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción explícita del estado actual (opcional, alimentado por Proveedores)"
    )

    # 7. Placa del vehículo (con índice para búsquedas rápidas)
    placa = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Placa del vehículo"
    )

    # 8. Departamento (ForeignKey al modelo Departamento)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='tramites_tracker',
        db_column='departamento_id',
        help_text="Departamento del trámite"
    )

    # 9. Municipio (ForeignKey al modelo Municipio)
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='tramites_tracker',
        db_column='municipio_id',
        help_text="Municipio del trámite"
    )

    # 10. Tipo de vehículo
    tipo_vehiculo = models.CharField(
        max_length=20,
        choices=TIPO_VEHICULO_CHOICES,
        help_text="Tipo de vehículo del trámite"
    )

    # 11. Código de encargado (Relación con Proveedor)
    # DECISIÓN: Usamos ForeignKey a Proveedor porque existe un modelo Proveedor
    # con campo `codigo_encargado` único. Esto permite trazabilidad y validación.
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='tramites_tracker',
        db_column='proveedor_id',
        help_text="Proveedor encargado del trámite (identificado por codigo_encargado)",
        null=True,
        blank=True
    )

    # 12. Paquete (relación con Preparación)
    # DECISIÓN: Usamos ForeignKey a Preparacion porque el trámite proviene
    # del módulo "En preparación" y necesitamos mantener la trazabilidad.
    preparacion = models.ForeignKey(
        Preparacion,
        on_delete=models.PROTECT,
        related_name='radicaciones',
        db_column='preparacion_id',
        help_text="Trámite de preparación asociado (paquete PDF)",
        null=True,
        blank=True
    )

    # Timestamps automáticos
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación del registro"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización"
    )

    # Historial de cambios con django-simple-history
    history = HistoricalRecords(
        table_name='history_tracker',
        verbose_name='Historial de Tracker',
        related_name='historico'
    )

    class Meta:
        db_table = "tracker"
        verbose_name = "Trámite en Tracker"
        verbose_name_plural = "Trámites en Tracker"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['placa'], name='idx_tracker_placa'),
            models.Index(fields=['estado'], name='idx_tracker_estado'),
            models.Index(fields=['proveedor'], name='idx_tracker_proveedor'),
            models.Index(fields=['fecha_recepcion_municipio'], name='idx_tracker_fecha_recep'),
            models.Index(fields=['created_at'], name='idx_tracker_created'),
        ]

    def __str__(self):
        return f"{self.placa} - {self.get_estado_display()}"

    # 4. Hace (antigüedad del registro en días) - PROPIEDAD CALCULADA
    @property
    def hace_dias(self):
        """
        Calcula la antigüedad del trámite en días desde la fecha de recepción
        en el municipio hasta hoy.

        Returns:
            int or None: Número de días transcurridos desde la recepción,
                        o None si no hay fecha de recepción.

        Nota: Se usa timezone.now().date() para garantizar cálculos timezone-aware.
        """
        if not self.fecha_recepcion_municipio:
            return None

        hoy = timezone.now().date()
        dias = (hoy - self.fecha_recepcion_municipio).days
        return dias

    @property
    def codigo_encargado(self):
        """
        Propiedad de solo lectura que retorna el código del proveedor encargado.

        Returns:
            str or None: Código del encargado o None si no hay proveedor asignado.
        """
        return self.proveedor.codigo_encargado if self.proveedor else None
