from django.contrib import admin
from .models import DashboardBanner, DashboardPopup, EmployeeMessage

@admin.register(DashboardBanner)
class DashboardBannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'uploaded_by', 'created_at')
    list_filter = ('is_active',)

@admin.register(DashboardPopup)
class DashboardPopupAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'uploaded_by', 'created_at')
    list_filter = ('is_active',)

@admin.register(EmployeeMessage)
class EmployeeMessageAdmin(admin.ModelAdmin):
    list_display = ('employee', 'category', 'subject', 'status', 'is_urgent', 'created_at')
    list_filter = ('status', 'category', 'is_urgent')
    search_fields = ('employee__employee_code', 'employee__user__first_name', 'employee__user__last_name', 'subject', 'message')
