from django.db import models
from decimal import Decimal
from simple_history.models import HistoricalRecords

from preparacion.models import Preparacion
from tramites.models import Tramite
from proveedores.models import Proveedor
from clientes.models import Cliente
from departamentos.models import Departamento
from municipios.models import Municipio


class Liquidacion(models.Model):
    """
    Registro de liquidación de un trámite finalizado.
    Almacena todos los datos económicos para el cálculo de utilidad.
    """

    # Referencia al trámite de preparación (el registro principal)
    preparacion = models.OneToOneField(
        Preparacion,
        on_delete=models.CASCADE,
        related_name='liquidacion',
        help_text="Trámite de preparación asociado"
    )

    # Tipo de trámite
    tramite = models.ForeignKey(
        Tramite,
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        null=True,
        blank=True,
        help_text="Tipo de trámite realizado"
    )

    # Proveedor/Gestor
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        null=True,
        blank=True,
        help_text="Gestor que realizó el trámite"
    )

    # Cliente
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        null=True,
        blank=True,
        help_text="Cliente del trámite"
    )

    # Ubicación
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        null=True,
        blank=True,
        help_text="Departamento del trámite"
    )
    municipio = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='liquidaciones',
        null=True,
        blank=True,
        help_text="Municipio del trámite"
    )

    # === Datos de Facturación ===
    # Derechos del trámite (precio base del trámite)
    derechos_tramite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Derechos/precio del trámite"
    )

    # Servicio que cobra la empresa al cliente
    servicio_empresa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Precio que cobra la empresa al cliente"
    )

    # === Datos del Servicio Gestor ===
    # Lo que se paga al gestor
    servicio_gestor = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Precio que se paga al gestor"
    )

    # Transporte/Envíos
    transporte = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Gastos de transporte/envíos"
    )

    # Bonificación
    bonificacion = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Bonificación al gestor"
    )

    # Anticipos (descuento)
    anticipos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Anticipos entregados al gestor"
    )

    # === Información adicional ===
    placa = models.CharField(
        max_length=20,
        help_text="Placa del vehículo"
    )
    tipo_vehiculo = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tipo de vehículo"
    )

    # Fecha de finalización del trámite
    fecha_finalizado = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha de finalización del trámite"
    )

    # Observaciones
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )

    # Estado de la liquidación
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de revisión'),
        ('aprobada', 'Aprobada'),
        ('pagada', 'Pagada'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        help_text="Estado de la liquidación"
    )

    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Historial
    history = HistoricalRecords()

    class Meta:
        db_table = 'liquidaciones'
        verbose_name = 'Liquidación'
        verbose_name_plural = 'Liquidaciones'
        ordering = ['-fecha_finalizado']
        indexes = [
            models.Index(fields=['placa']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_finalizado']),
            models.Index(fields=['proveedor']),
            models.Index(fields=['tramite']),
        ]

    def __str__(self):
        return f"Liquidación {self.placa} - {self.tramite.nombre if self.tramite else 'N/A'}"

    # === Propiedades calculadas ===

    @property
    def iva_porcentaje(self):
        """Porcentaje de IVA aplicado"""
        return Decimal('0.19')

    @property
    def iva_servicio(self):
        """IVA del servicio empresa (19%)"""
        return self.servicio_empresa * self.iva_porcentaje

    @property
    def total_facturacion(self):
        """Total de facturación (derechos + servicio empresa + IVA)"""
        return self.derechos_tramite + self.servicio_empresa + self.iva_servicio

    @property
    def total_facturacion_sin_iva(self):
        """Total de facturación sin IVA"""
        return self.derechos_tramite + self.servicio_empresa

    @property
    def total_servicio_gestor(self):
        """Total a pagar al gestor (servicio + transporte + bonificación - anticipos)"""
        return self.servicio_gestor + self.transporte + self.bonificacion - self.anticipos

    @property
    def utilidad(self):
        """Utilidad = Facturación sin IVA - Total servicio gestor"""
        return self.total_facturacion_sin_iva - self.total_servicio_gestor

    @property
    def es_rentable(self):
        """Indica si el trámite fue rentable"""
        return self.utilidad >= 0
