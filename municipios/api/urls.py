from django.urls import path
from . import views

urlpatterns = [
    path('list/<int:id_departamento>/', views.list_municipios,  name='list_municipios'),
]