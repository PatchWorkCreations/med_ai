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


# myApp/middleware.py
import ipaddress, re
from typing import Optional
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache

DEFAULT_COUNTRY = "US"  # safest fallback

def _client_ip(request) -> str:
    return (
        request.META.get("HTTP_CF_CONNECTING_IP")  # Cloudflare direct client IP
        or (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
        or request.META.get("REMOTE_ADDR", "")
    )

def _is_private(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except Exception:
        return True

def _country_from_accept_language(al: Optional[str]) -> Optional[str]:
    if not al:
        return None
    for token in al.split(","):
        token = token.split(";")[0].strip()  # e.g., en-PH
        m = re.match(r"^[A-Za-z]{2,3}-(?P<region>[A-Za-z]{2})$", token)
        if m:
            return m.group("region").upper()
        if token.lower() in ("fil", "tl", "tagalog"):
            return "PH"
    return None

def _country_from_http(ip: str) -> Optional[str]:
    """
    Lightweight HTTPS lookup with caching (24h).
    Uses ipwho.is (no auth required). Safe to remove if you want 100% offline.
    """
    if not ip or _is_private(ip):
        return None
    key = "ipcc:%s" % ip
    cached = cache.get(key)
    if cached:
        return cached
    try:
        import requests  # if not installed, just `pip install requests`
        r = requests.get("https://ipwho.is/%s?fields=country_code" % ip, timeout=1.8)
        if r.ok:
            data = r.json() or {}
            cc = data.get("country_code")
            if cc and len(cc) == 2:
                cc = cc.upper()
                cache.set(key, cc, 60 * 60 * 24)
                return cc
    except Exception:
        pass
    return None

class CountryMiddleware(MiddlewareMixin):
    """
    Attaches request.country_code (e.g., 'PH') for downstream use.
    Order:
      1) CDN headers
      2) HTTP fallback (ipwho.is), cached 24h
      3) Accept-Language
      4) Dev default (PH if DEBUG; else US)
      5) DEFAULT_COUNTRY
    """
    def process_request(self, request):
        # 1) CDN headers
        for key in (
            "HTTP_CF_IPCOUNTRY",
            "HTTP_CLOUDFRONT_VIEWER_COUNTRY",
            "HTTP_X_APPENGINE_COUNTRY",
            "HTTP_X_GEO_COUNTRY",
        ):
            val = request.META.get(key)
            if val and len(val) == 2:
                request.country_code = val.upper()
                return

        ip = _client_ip(request)

        # 2) HTTP fallback (cached)
        cc = _country_from_http(ip)
        if cc:
            request.country_code = cc
            return

        # 3) Accept-Language
        cc = _country_from_accept_language(request.META.get("HTTP_ACCEPT_LANGUAGE"))
        if cc:
            request.country_code = cc
            return

        # 4) Localhost dev default
        host = (request.get_host() or "").lower()
        if host.startswith(("127.0.0.1", "localhost")):
            try:
                from django.conf import settings
                request.country_code = "PH" if getattr(settings, "DEBUG", False) else DEFAULT_COUNTRY
                return
            except Exception:
                pass

        # 5) Final fallback
        request.country_code = DEFAULT_COUNTRY
