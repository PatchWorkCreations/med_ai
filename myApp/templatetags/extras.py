# myApp/templatetags/extras.py
from django import template

register = template.Library()

@register.filter
def split(value, sep=","):
    """
    Safe split: if value is already a list, return as-is.
    Usage: {{ "A,B,C"|split:"," }}
    """
    if isinstance(value, (list, tuple)):
        return list(value)
    if value is None:
        return []
    return str(value).split(sep)

@register.filter
def get(d, key):
    try:
        return d.get(key)
    except Exception:
        return None

@register.filter
def priority_badge(priority):
    p = (priority or "").lower()
    if p == "high":
        return ("bg-rose-50", "text-rose-700", "High")
    if p == "low":
        return ("bg-emerald-50", "text-emerald-700", "Low")
    return ("bg-amber-50", "text-amber-700", "Medium")