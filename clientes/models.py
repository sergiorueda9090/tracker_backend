from django.db import models
from simple_history.models import HistoricalRecords
from departamentos.models import Departamento
from municipios.models import Municipio


class Cliente(models.Model):
    """Modelo para gestionar clientes"""

    nombre = models.CharField(
        max_length=255,
        help_text="Nombre del cliente"
    )

    razon_social = models.CharField(
        max_length=255,
        help_text="Razón social del cliente"
    )

    nit = models.CharField(
        max_length=50,
        unique=True,
        help_text="NIT del cliente"
    )

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='clientes',
        db_column='departamento_id',
        help_text="Departamento del cliente"
    )

    ciudad = models.ForeignKey(
        Municipio,
        on_delete=models.PROTECT,
        related_name='clientes',
        db_column='ciudad_id',
        help_text="Ciudad/Municipio del cliente"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['nit'], name='idx_cliente_nit'),
            models.Index(fields=['departamento', 'ciudad'], name='idx_cliente_ubicacion'),
            models.Index(fields=['is_active'], name='idx_cliente_activo'),
        ]

    def __str__(self):
        return f"{self.nit} - {self.nombre}"
