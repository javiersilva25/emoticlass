from functools import wraps
from flask import session, abort

def roles_required(*roles):
    allowed = set(roles)
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            role = session.get("user_role")
            if role not in allowed:
                abort(403)
            return fn(*args, **kwargs)
        return inner
    return wrapper
