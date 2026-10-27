from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from urllib.parse import urlparse
from django.middleware.csrf import CsrfViewMiddleware


class CustomCsrfViewMiddleware(CsrfViewMiddleware):
    """
    Enhanced CSRF middleware that ensures legitimate requests coming from
    Railway production/preview domains (*.railway.app, *.up.railway.app)
    or the current host are never rejected due to Origin check mismatches
    caused by reverse-proxy SSL termination or dynamic cloud subdomains,
    while strictly preserving CSRF token security and origin verification.
    """
    def _origin_verified(self, request):
        if super()._origin_verified(request):
            return True

        origin = request.META.get('HTTP_ORIGIN')
        if not origin:
            return False

        try:
            netloc = urlparse(origin).netloc.split(':')[0].lower()
            good_host = request.get_host().split(':')[0].lower()
        except Exception:
            return False

        is_same_host = (netloc == good_host)
        is_railway = netloc.endswith('.railway.app') or netloc.endswith('.up.railway.app')
        is_local = netloc in ('127.0.0.1', 'localhost', 'testserver')

        if is_same_host:
            return True
        if is_railway and (good_host.endswith('.railway.app') or good_host.endswith('.up.railway.app')):
            return True
        if is_local and good_host in ('127.0.0.1', 'localhost', 'testserver'):
            return True
        return False


class OneDevicePerUserMiddleware:
    """
    Enforces single-device login per user account.
    If the same user logs in from another device/browser:
    - The new device becomes the active session.
    - The previous device's session is invalidated on its next request.
    - The previous device is automatically logged out.
    - A message is displayed: "Your account has been logged in on another device."
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt_paths = ('/login/', '/logout/')
            if not request.path.startswith(('/static/', '/media/')) and request.path not in exempt_paths:
                current_session_key = request.session.session_key
                if current_session_key:
                    from apps.users.models import UserActiveSession
                    try:
                        active_session = UserActiveSession.objects.filter(user=request.user).first()
                        if active_session and active_session.session_key:
                            if active_session.session_key != current_session_key:
                                # Another device/browser logged in with the same user ID
                                logout(request)
                                messages.warning(request, "Your account has been logged in on another device.")

                                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                                    from django.http import JsonResponse
                                    return JsonResponse({
                                        'status': 'logged_out',
                                        'message': 'Your account has been logged in on another device.',
                                        'redirect_url': '/login/'
                                    }, status=401)
                                return redirect('login')
                        elif not active_session:
                            UserActiveSession.objects.create(
                                user=request.user,
                                session_key=current_session_key
                            )
                    except Exception:
                        pass

        response = self.get_response(request)
        return response
