from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_archivada, name='create_archivada'),
    path('list/', views.list_archivadas, name='list_archivadas'),
    path('<int:pk>/', views.get_archivada, name='get_archivada'),
    path('<int:pk>/update/', views.update_archivada, name='update_archivada'),
    path('<int:pk>/delete/', views.delete_archivada, name='delete_archivada'),
    path('<int:pk>/history/', views.get_archivada_history, name='get_archivada_history'),
]
