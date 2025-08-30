ROLES = ["admin", "administrativo", "profesor", "convivencia", "utp"]

def is_valid_role(role: str) -> bool:
    return role in ROLES
