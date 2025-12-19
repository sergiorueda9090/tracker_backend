from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.list_departamentos,  name='list_departamentos'),
]