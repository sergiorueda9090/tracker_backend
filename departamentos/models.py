from django.db import models

# Create your models here.
class Departamento(models.Model):
    """Modelo para almacenar departamentos de Colombia"""
    
    id_departamento = models.IntegerField(
        primary_key=True,
        help_text="Código DANE del departamento"
    )
    
    departamento = models.CharField(
        max_length=255,
        unique=True,
        help_text="Nombre del departamento"
    )

    class Meta:
        db_table = "departamentos"
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['departamento']

    def __str__(self):
        return self.departamento