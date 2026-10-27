from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver


class UserActiveSession(models.Model):
    """
    Tracks the single active session for each user account.
    Enforces one device/browser login at a time.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='active_session',
        verbose_name='User'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text='Current active session key for single device enforcement'
    )
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Active Session'
        verbose_name_plural = 'User Active Sessions'
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.username} (Active Session: {self.session_key or 'None'})"


@receiver(user_logged_in)
def on_user_logged_in_sync_session(sender, request, user, **kwargs):
    """
    Signal receiver triggered upon any successful login (portal or admin).
    Updates or creates UserActiveSession with the current session key.
    """
    if request:
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key
        if session_key:
            UserActiveSession.objects.update_or_create(
                user=user,
                defaults={'session_key': session_key}
            )
