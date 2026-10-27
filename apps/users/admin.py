from django.contrib import admin
from .models import UserActiveSession


@admin.register(UserActiveSession)
class UserActiveSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'last_activity')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'session_key')
    readonly_fields = ('last_activity',)
