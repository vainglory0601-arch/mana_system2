# accounts/templatetags/custom_filters.py
from django import template
from urllib.parse import unquote

register = template.Library()

@register.filter
def urldecode(value):
    """Decode URL encoded string"""
    if not value:
        return value
    return unquote(str(value))