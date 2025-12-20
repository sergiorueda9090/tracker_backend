from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_tramite, name='create_tramite'),
    path('list/', views.list_tramites, name='list_tramites'),
    path('<int:pk>/', views.get_tramite, name='get_tramite'),
    path('<int:pk>/update/', views.update_tramite, name='update_tramite'),
    path('<int:pk>/delete/', views.delete_tramite, name='delete_tramite'),
    path('archivo/<int:archivo_id>/delete/', views.delete_archivo, name='delete_archivo'),
    path('<int:pk>/history/', views.get_tramite_history, name='get_tramite_history'),
]