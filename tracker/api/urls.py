from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_tracker, name='create_tracker'),
    path('list/', views.list_trackers, name='list_trackers'),
    path('<int:pk>/', views.get_tracker, name='get_tracker'),
    path('<int:pk>/update/', views.update_tracker, name='update_tracker'),
    path('<int:pk>/delete/', views.delete_tracker, name='delete_tracker'),
    path('<int:pk>/history/', views.get_tracker_history, name='get_tracker_history'),
]
