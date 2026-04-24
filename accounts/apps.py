from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        # Fix Jazzmin + Django 6 format_html() TypeError
        try:
            from django.utils.safestring import mark_safe
            from django.utils import html as django_html
            import jazzmin.templatetags.jazzmin as jm

            def safe_format_html(format_string, *args, **kwargs):
                # Django 6 raises if no args/kwargs, so handle it
                if not args and not kwargs:
                    return mark_safe(format_string)
                return django_html.format_html(format_string, *args, **kwargs)

            jm.format_html = safe_format_html
        except Exception:
            # don't break startup if jazzmin not installed
            pass