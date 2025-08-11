from django import template
register = template.Library()

@register.filter
def add_class(field, css):
    # merges with existing attrs
    attrs = field.field.widget.attrs.copy()
    existing = attrs.get("class", "")
    attrs["class"] = f"{existing} {css}".strip() if existing else css
    return field.as_widget(attrs=attrs)
