from django.db import models
from simple_history.models import HistoricalRecords
from tramites.models import Tramite
from proveedores.models import Proveedor


class TransitoTarifa(models.Model):
    """
    Modelo para gestionar las tarifas de tránsitos por proveedor.
    Relaciona trámites con proveedores y define los precios de servicio.
    """
    tramite = models.ForeignKey(
        Tramite,
        on_delete=models.PROTECT,
        related_name='transito_tarifas',
        help_text="Trámite asociado a esta tarifa"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='transito_tarifas',
        help_text="Proveedor que gestiona este tránsito"
    )
    servicio_proveedor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio del servicio que cobra el proveedor"
    )
    servicio_empresa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio del servicio que cobra la empresa"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la tarifa está activa"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización"
    )

    # Audit trail
    history = HistoricalRecords()

    class Meta:
        db_table = 'transito_tarifas'
        verbose_name = 'Tránsito Tarifa'
        verbose_name_plural = 'Tránsitos Tarifas'
        ordering = ['tramite__nombre', 'proveedor__nombre']
        unique_together = [['tramite', 'proveedor']]
        indexes = [
            models.Index(fields=['tramite', 'proveedor']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.tramite.nombre} - {self.proveedor.nombre}"

    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia de la empresa"""
        return self.servicio_empresa - self.servicio_proveedor

    @property
    def porcentaje_margen(self):
        """Calcula el porcentaje de margen sobre el precio del proveedor"""
        if self.servicio_proveedor > 0:
            return (self.margen_ganancia / self.servicio_proveedor) * 100
        return 0
