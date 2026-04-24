from django.shortcuts import redirect
from functools import wraps

def block_if_frozen(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        account_status = getattr(request.user, "account_status", "ACTIVE")
        if account_status.upper() == "FROZEN":
            return redirect("/dashboard/?frozen=1")
        return view_func(request, *args, **kwargs)
    return _wrapped
