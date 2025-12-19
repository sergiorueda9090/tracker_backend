from django.db import models
from departamentos.models import Departamento

# Create your models here.
class Municipio(models.Model):
    """Modelo para almacenar municipios de Colombia"""
    
    id_municipio = models.AutoField(
        primary_key=True,
        help_text="ID único del municipio"
    )
    
    municipio = models.CharField(
        max_length=255,
        help_text="Nombre del municipio"
    )
    
    estado = models.BooleanField(
        default=True,
        help_text="Estado del municipio (activo/inactivo)"
    )
    
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.PROTECT,
        related_name='municipios',
        db_column='departamento_id',
        help_text="Departamento al que pertenece"
    )

    class Meta:
        db_table = "municipios"
        verbose_name = "Municipio"
        verbose_name_plural = "Municipios"
        ordering = ["departamento__departamento", "municipio"]
        indexes = [
            models.Index(fields=['departamento', 'municipio'], name='idx_mun_dept_nombre'),
            models.Index(fields=['estado'], name='idx_mun_estado'),
        ]

    def __str__(self):
        return f"{self.municipio} - {self.departamento.departamento}"
