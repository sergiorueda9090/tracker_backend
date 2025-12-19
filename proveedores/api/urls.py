from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_proveedor, name='create_proveedor'),
    path('list/', views.list_proveedores, name='list_proveedores'),
    path('<int:pk>/', views.get_proveedor, name='get_proveedor'),
    path('<int:pk>/update/', views.update_proveedor, name='update_proveedor'),
    path('<int:pk>/delete/', views.delete_proveedor, name='delete_proveedor'),
]