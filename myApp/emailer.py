# myApp/emailer.py
import json, logging, requests
from typing import Iterable, Optional, Union
from django.conf import settings

log = logging.getLogger(__name__)

RESEND_URL = f"{settings.RESEND.get('BASE_URL', 'https://api.resend.com')}/emails"
RESEND_KEY = settings.RESEND.get("API_KEY")
RESEND_FROM = settings.RESEND.get("FROM") or settings.DEFAULT_FROM_EMAIL
RESEND_REPLY_TO = settings.RESEND.get("REPLY_TO")

def send_via_resend(
    *,
    to: Union[Iterable[str], str],
    subject: str,
    text: Optional[str] = None,
    html: Optional[str] = None,
    from_email: Optional[str] = None,
    reply_to: Optional[Union[Iterable[str], str]] = None,
    cc: Optional[Iterable[str]] = None,
    bcc: Optional[Iterable[str]] = None,
    tags: Optional[dict] = None,
    fail_silently: bool = True,
) -> bool:
    """
    Minimal Resend sender. Returns True on 2xx. Logs (doesn't raise) by default.
    """
    if not RESEND_KEY:
        msg = "RESEND_API_KEY missing; email not sent."
        if fail_silently:
            log.warning(msg); return False
        raise RuntimeError(msg)

    if isinstance(to, str): to = [to]
    if isinstance(reply_to, str): reply_to = [reply_to]

    payload = {
        "from": (from_email or RESEND_FROM),
        "to": list(to),
        "subject": subject,
    }
    if text: payload["text"] = text
    if html: payload["html"] = html
    if reply_to or RESEND_REPLY_TO:
        payload["reply_to"] = reply_to or [RESEND_REPLY_TO]
    if cc: payload["cc"] = list(cc)
    if bcc: payload["bcc"] = list(bcc)
    if tags:
        # Resend supports tags via headers (x-headers) or metadata; keep simple:
        payload["headers"] = {f"X-Tag-{k}": str(v) for k, v in tags.items()}

    try:
        resp = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10,
        )
        ok = 200 <= resp.status_code < 300
        if not ok:
            log.error("Resend send failed: %s %s", resp.status_code, resp.text)
        return ok
    except Exception as e:
        if fail_silently:
            log.exception("Resend exception")
            return False
        raise
