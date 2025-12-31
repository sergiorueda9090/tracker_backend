from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_finalizado, name='create_finalizado'),
    path('list/', views.list_finalizados, name='list_finalizados'),
    path('<int:pk>/', views.get_finalizado, name='get_finalizado'),
    path('<int:pk>/update/', views.update_finalizado, name='update_finalizado'),
    path('<int:pk>/delete/', views.delete_finalizado, name='delete_finalizado'),
    path('<int:pk>/history/', views.get_finalizado_history, name='get_finalizado_history'),
]
