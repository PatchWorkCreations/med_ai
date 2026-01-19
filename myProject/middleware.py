"""
Custom middleware for the project.
"""
from django.utils.deprecation import MiddlewareMixin


class DisableCSRFForAPI(MiddlewareMixin):
    """
    Disable CSRF protection for mobile API endpoints only.
    Mobile API uses token-based authentication, not session-based.
    Main website API endpoints still use CSRF protection.
    """
    def process_request(self, request):
        # Disable CSRF for mobile API paths and webapp API endpoints
        if request.path.startswith('/api/mobile/') or request.path.startswith('/webapp/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None


class BusyModeMiddleware(MiddlewareMixin):
    """
    Placeholder middleware for busy mode functionality.
    Can be implemented later if needed.
    """
    def process_request(self, request):
        # Placeholder - no action needed
        return None
