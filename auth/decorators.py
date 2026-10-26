from functools import wraps
from flask import abort
from flask_login import current_user, login_required


def role_required(*roles):
    # usage: @role_required("admin") or @role_required("admin", "reviewer")
    def decorator(func):
        @wraps(func)
        @login_required  # must be logged in first
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)  # 403 = "you are not allowed"
            return func(*args, **kwargs)
        return wrapper
    return decorator