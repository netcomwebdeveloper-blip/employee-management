from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', auth_views.LoginView.as_view(template_name='core/login.html'), name='home'),
    path('front/', views.front_page, name='front_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('employee/', views.employee_dashboard, name='employee_dashboard'),
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('admin-page/', views.admin_dashboard, name='admin_dashboard'),

    path('delete-employee/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    path('leave/<int:leave_id>/<str:status>/', views.update_leave_status, name='update_leave_status'),
]