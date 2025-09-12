from functools import wraps
from django.http import HttpResponseForbidden

def org_required(view_fn):
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "org", None):
            return HttpResponseForbidden("Organization not selected.")
        return view_fn(request, *args, **kwargs)
    return wrapper

def role_required(*roles):
    def deco(view_fn):
        @wraps(view_fn)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.org:
                return HttpResponseForbidden("Not allowed.")
            mem = request.user.memberships.filter(org=request.org, is_active=True).first()
            if not mem or mem.role not in roles:
                return HttpResponseForbidden("Insufficient role.")
            return view_fn(request, *args, **kwargs)
        return wrapper
    return deco
