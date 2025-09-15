# myApp/utils.py
from typing import Tuple, Optional

def get_client_ip(request) -> str:
    """
    Best-effort public client IP. Honors reverse proxy headers.
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # e.g. "client, proxy1, proxy2" -> take first non-empty trimmed
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[0]
    return request.META.get("REMOTE_ADDR", "")

def get_country_from_request(request) -> Optional[str]:
    """
    Optional. Returns a 2-letter country code (e.g., 'PH') if you have a
    proxy/CDN adding Geo headers. Otherwise returns None.

    Common headers:
      - Cloudflare: CF-IPCountry
      - AWS ALB/CloudFront via Lambda@Edge: CloudFront-Viewer-Country
      - Some CDNs: X-AppEngine-Country, X-Geo-Country, etc.
    """
    for key in ("HTTP_CF_IPCOUNTRY", "HTTP_CLOUDFRONT_VIEWER_COUNTRY", "HTTP_X_APPENGINE_COUNTRY", "HTTP_X_GEO_COUNTRY"):
        val = request.META.get(key)
        if val and len(val) == 2:
            return val.upper()
    return None
