def require_admin(user):
    if user["type"] != "admin":
        raise PermissionError

def require_driver(user):
    if user["type"] != "driver":
        raise PermissionError
