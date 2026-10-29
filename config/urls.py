from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from apps.users import views as user_views

import os
from django.shortcuts import render

def safe_serve_media(request, path, document_root=None, show_indexes=False):
    root = document_root or settings.MEDIA_ROOT
    full_path = os.path.join(str(root), path)
    if not os.path.exists(full_path):
        return render(request, 'errors/media_not_found.html', {
            'path': path,
            'filename': os.path.basename(path)
        }, status=404)
    from django.views.static import serve
    return serve(request, path, document_root=root, show_indexes=show_indexes)

urlpatterns = [
    # Django Administration Backend
    path('django-admin/', admin.site.urls),

    # Authentication Routes (Exact preservation of /login/ and /logout/ URLs)
    path('', user_views.root_redirect_view, name='home'),
    path('login/', user_views.custom_login_view, name='login'),
    path('logout/', user_views.custom_logout_view, name='logout'),

    # Modular App Endpoints
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('employees/', include('apps.employees.urls', namespace='employees')),
    path('departments/', include('apps.departments.urls', namespace='departments')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('leave/', include('apps.leave_management.urls', namespace='leave_management')),
    path('payroll/', include('apps.payroll.urls', namespace='payroll')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('users/', include('apps.users.urls', namespace='users')),

    # Safe Media files serving in all environments
    re_path(r'^media/(?P<path>.*)$', safe_serve_media, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
