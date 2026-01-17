from django.db import models
from simple_history.models import HistoricalRecords
from tramites.models import Tramite
from proveedores.models import Proveedor
from departamentos.models import Departamento
from municipios.models import Municipio


class TransitoTarifa(models.Model):
    """
    Configuración de tarifas por ubicación geográfica.
    Un registro por cada departamento-municipio.
    """
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='transito_tarifas',
        help_text="Departamento donde aplica esta configuración"
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='transito_tarifas',
        help_text="Municipio donde aplica esta configuración"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si la configuración está activa"
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
        ordering = ['departamento__departamento', 'municipio__municipio']
        unique_together = [['departamento', 'municipio']]
        indexes = [
            models.Index(fields=['departamento', 'municipio']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.departamento.departamento} - {self.municipio.municipio}"


class TransitoTarifaTramite(models.Model):
    """
    Trámites configurados para una ubicación específica.
    Relaciona TransitoTarifa con Tramites y define los derechos.
    """
    transito_tarifa = models.ForeignKey(
        TransitoTarifa,
        on_delete=models.CASCADE,
        related_name='tramites',
        help_text="Configuración de ubicación a la que pertenece"
    )
    tramite = models.ForeignKey(
        Tramite,
        on_delete=models.PROTECT,
        related_name='transito_tarifas',
        help_text="Trámite configurado"
    )
    derechos_2026 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Derechos de tránsito para 2026"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización"
    )

    class Meta:
        db_table = 'transito_tarifa_tramites'
        verbose_name = 'Tránsito Tarifa Trámite'
        verbose_name_plural = 'Tránsitos Tarifas Trámites'
        ordering = ['tramite__nombre']
        unique_together = [['transito_tarifa', 'tramite']]
        indexes = [
            models.Index(fields=['transito_tarifa', 'tramite']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.transito_tarifa} - {self.tramite.nombre}"


class TransitoTarifaGestor(models.Model):
    """
    Gestores (proveedores) asignados a cada trámite.
    Contiene las tarifas del gestor y de la empresa.
    """
    tramite_tarifa = models.ForeignKey(
        TransitoTarifaTramite,
        on_delete=models.CASCADE,
        related_name='gestores',
        help_text="Trámite al que pertenece este gestor"
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='transito_tarifa_gestores',
        help_text="Proveedor/Gestor que realiza el trámite"
    )
    servicio_gestor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio que cobra el gestor"
    )
    servicio_empresa = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio que cobra la empresa al cliente"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de última actualización"
    )

    class Meta:
        db_table = 'transito_tarifa_gestores'
        verbose_name = 'Tránsito Tarifa Gestor'
        verbose_name_plural = 'Tránsitos Tarifas Gestores'
        ordering = ['proveedor__nombre']
        unique_together = [['tramite_tarifa', 'proveedor']]
        indexes = [
            models.Index(fields=['tramite_tarifa', 'proveedor']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.tramite_tarifa.tramite.nombre} - {self.proveedor.nombre}"

    @property
    def margen_ganancia(self):
        """Calcula el margen de ganancia de la empresa"""
        return self.servicio_empresa - self.servicio_gestor

    @property
    def porcentaje_margen(self):
        """Calcula el porcentaje de margen sobre el precio del gestor"""
        if self.servicio_gestor > 0:
            return (self.margen_ganancia / self.servicio_gestor) * 100
        return 0
