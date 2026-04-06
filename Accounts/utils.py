from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def site_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        if request.user.site_role != "SITE_ADMIN":
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper
