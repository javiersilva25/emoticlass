import hashlib

def validar_rut(rut: str) -> bool:
    if not rut: return False
    rut = rut.replace(".", "").replace("-", "").upper()
    if len(rut) < 2: return False
    num, dv = rut[:-1], rut[-1]
    if not num.isdigit(): return False
    suma, mul = 0, 2
    for d in reversed(num):
        suma += int(d) * mul
        mul = 2 if mul == 7 else mul + 1
    dv_calc = 11 - (suma % 11)
    dv_calc = '0' if dv_calc == 11 else ('K' if dv_calc == 10 else str(dv_calc))
    return dv == dv_calc

def limpiar_rut(rut: str) -> str:
    return rut.replace(".", "").replace("-", "").upper()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
