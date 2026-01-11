from django.db import models
from simple_history.models import HistoricalRecords


class Tramite(models.Model):
    """
    Modelo para gestionar los diferentes tipos de trámites disponibles.
    """
    nombre = models.CharField(
        max_length=200,
        unique=True,
        help_text="Nombre del trámite"
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción detallada del trámite"
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio del trámite en pesos colombianos"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si el trámite está activo"
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
        db_table = 'tramites'
        verbose_name = 'Trámite'
        verbose_name_plural = 'Trámites'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"
