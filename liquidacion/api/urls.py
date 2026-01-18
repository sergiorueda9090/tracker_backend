from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.list_liquidaciones, name='list_liquidaciones'),
    path('estadisticas/', views.get_estadisticas, name='get_estadisticas'),
    path('<int:pk>/', views.get_liquidacion, name='get_liquidacion'),
    path('<int:pk>/update/', views.update_liquidacion, name='update_liquidacion'),
    path('preparacion/<int:preparacion_id>/', views.get_liquidacion_by_preparacion, name='get_liquidacion_by_preparacion'),
]
