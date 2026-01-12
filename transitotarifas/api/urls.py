from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_transito_tarifa, name='create_transito_tarifa'),
    path('list/', views.list_transito_tarifas, name='list_transito_tarifas'),
    path('<int:pk>/', views.get_transito_tarifa, name='get_transito_tarifa'),
    path('<int:pk>/update/', views.update_transito_tarifa, name='update_transito_tarifa'),
    path('<int:pk>/delete/', views.delete_transito_tarifa, name='delete_transito_tarifa'),
]
