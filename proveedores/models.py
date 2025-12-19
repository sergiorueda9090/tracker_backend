from django.db import models
from user.models import User


class Proveedor(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='proveedores',
        db_column='user_id',
        null=True,
        blank=True
    )
    
    codigo_encargado = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=255)
    whatsapp = models.CharField(max_length=20)
    departamento = models.CharField(max_length=100, blank=True)
    municipio = models.CharField(max_length=100, blank=True)  # ✅ Agregado blank=True
    transitos_habilitados = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proveedores"
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.codigo_encargado} - {self.nombre}"