from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def home(request):
    if not request.user.is_authenticated:
        return redirect("choose")
    return redirect("/dashboard/")

urlpatterns = [
    path("admin/", admin.site.urls),           # ✅ admin here only
    path("", home, name="home"),
    path("", include("accounts.urls")),        # your main app
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)