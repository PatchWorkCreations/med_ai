from django.http import HttpResponseNotFound, HttpResponseForbidden
from django.conf import settings
from .models import OrgDomain, OrgMembership, set_current_org

# Scope multi-tenant behavior ONLY to these path prefixes
PORTAL_PATH_PREFIXES = ("/portal/",)  # add "/portal-api/" later if you split APIs

def _host_without_port(host_header: str) -> str:
    return (host_header or "").split(":")[0].lower().strip()

def _path_is_portal(path: str) -> bool:
    return any(path.startswith(p) for p in PORTAL_PATH_PREFIXES)

def _is_public_portal_path(path: str) -> bool:
    # Public routes within the portal space (no membership required)
    public = (
        "/portal/login/",
        "/portal/logout/",     # if you expose it unauthenticated
        "/portal/password",    # your OTP flows if routed under /portal/password*
        "/static/", "/media/", # assets
        "/healthz", "/ping",
    )
    return any(path.startswith(p) for p in public)

class CurrentOrgByHostMiddleware:
    """
    For /portal/* requests:
      - Map host -> Org via OrgDomain.
      - 404 unknown hosts in production.
      - Set request.org + thread-local for scoped managers.
    For non-portal paths:
      - Do nothing (keeps legacy app behavior intact).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not _path_is_portal(path):
            # Not a portal request — leave request.org unset and pass through.
            return self.get_response(request)

        host = _host_without_port(request.get_host())
        dom = OrgDomain.objects.select_related("org").filter(
            domain=host, org__is_active=True
        ).first()

        request.org = dom.org if dom else None
        set_current_org(request.org)

        # Unknown tenant host? Hide it in prod.
        if not settings.DEBUG and request.org is None:
            set_current_org(None)
            return HttpResponseNotFound("Not found.")

        try:
            response = self.get_response(request)
        finally:
            set_current_org(None)

        return response


class EnforceOrgMembershipMiddleware:
    """
    For /portal/* requests:
      - If authenticated, user must belong to request.org (active).
      - If unauthenticated and not a public portal path, let view handle (usually redirects).
    For non-portal paths:
      - Do nothing (keeps legacy app behavior intact).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not _path_is_portal(path):
            return self.get_response(request)  # legacy app path; no portal enforcement

        # Allow public portal paths (login, assets, health checks)
        if _is_public_portal_path(path):
            return self.get_response(request)

        org = getattr(request, "org", None)
        user = getattr(request, "user", None)

        # If there's somehow no org bound on a portal path, treat as 404 in prod
        if org is None and not settings.DEBUG:
            return HttpResponseNotFound("Not found.")

        # Unauthenticated requests proceed; the view/decorator will redirect to /portal/login/
        if not (user and user.is_authenticated):
            return self.get_response(request)

        # Staff to /admin/ is outside /portal/, so it never hits this branch.

        # Authenticated: must be a member of this org
        is_member = OrgMembership.objects.filter(
            user=user, org=org, is_active=True
        ).exists()

        if not is_member:
            return HttpResponseForbidden("You do not have access to this organization.")

        return self.get_response(request)
