import os
from django.shortcuts import render

class BusyModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Toggle via env var or cache/feature flag
        if os.environ.get("NM_BUSY_MODE") == "1":
            resp = render(request, "503.html", status=503)
            resp["Retry-After"] = "120"
            return resp
        return self.get_response(request)
