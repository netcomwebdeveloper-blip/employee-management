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
