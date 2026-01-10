from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_cliente, name='create_cliente'),
    path('list/', views.list_clientes, name='list_clientes'),
    path('<int:pk>/', views.get_cliente, name='get_cliente'),
    path('<int:pk>/update/', views.update_cliente, name='update_cliente'),
    path('<int:pk>/delete/', views.delete_cliente, name='delete_cliente'),
]
