from django.urls import path
from . import views

app_name = 'leave_management'

urlpatterns = [
    path('', views.leave_list, name='list'),
    path('request-permission/', views.request_permission, name='request_permission'),
    path('<int:pk>/review/', views.leave_status_update, name='review'),
    path('<int:pk>/<str:status>/', views.leave_status_update, name='status_update'),
]
