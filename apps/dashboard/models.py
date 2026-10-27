from django.db import models
from django.contrib.auth.models import User

class DashboardBanner(models.Model):
    title = models.CharField(max_length=200, default='Corporate Announcement & Updates')
    image = models.ImageField(upload_to='dashboard_banners/')
    banner_height = models.CharField(max_length=50, default='185px', blank=True)
    banner_width = models.CharField(max_length=50, default='100%', blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dashboard Banner'
        verbose_name_plural = 'Dashboard Banners'

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def get_active_banner(cls):
        return cls.objects.filter(is_active=True).first()


class DashboardPopup(models.Model):
    title = models.CharField(max_length=200, default='Netcom Corporate Announcement')
    image = models.ImageField(upload_to='dashboard_popups/')
    description = models.TextField(blank=True, default='')
    popup_width = models.CharField(max_length=50, default='650px', blank=True)
    popup_height = models.CharField(max_length=50, default='auto', blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Dashboard Popup'
        verbose_name_plural = 'Dashboard Popups'

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"

    @classmethod
    def get_active_popup(cls):
        return cls.objects.filter(is_active=True).first()
