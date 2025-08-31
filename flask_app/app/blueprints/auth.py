import re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

from ..utils.rut import validar_rut
from ..utils.db import verificar_usuario, crear_usuario

bp_auth = Blueprint("auth", __name__)

# Redirige a usuarios autenticados que intenten ver login/register
@bp_auth.before_app_request
def _redir_si_autenticado():
    if session.get("logged_in") and request.endpoint in ("auth.login", "auth.register"):
        return redirect(url_for("core.config"))

@bp_auth.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        rut = request.form.get("rut", "").strip()
        pwd = request.form.get("password", "").strip()

        if not rut or not pwd:
            flash("Por favor, complete todos los campos", "danger")
            return render_template("login.html")

        if not validar_rut(rut):
            flash("RUT inválido", "danger")
            return render_template("login.html")

        u = verificar_usuario(rut, pwd)
        if u:
            session.update({
                "logged_in": True,
                "user_id": u["id"],
                "user_name": u["nombre"],
                "user_rut": u["rut"],
                "user_email": u["correo"],
                "user_role": u["rol"],
            })
            flash(f"Bienvenido, {u['nombre']}", "success")
            return redirect(url_for("core.config"))

        flash("RUT o contraseña incorrectos", "danger")

    return render_template("login.html")

@bp_auth.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        rut = request.form.get("rut", "").strip()
        nombre = request.form.get("nombre_completo", "").strip()
        correo = request.form.get("correo", "").strip()
        pwd = request.form.get("password", "").strip()
        cpwd = request.form.get("confirm_password", "").strip()

        if not all([rut, nombre, correo, pwd, cpwd]):
            flash("Por favor, complete todos los campos", "danger")
            return render_template("register.html")

        if not validar_rut(rut):
            flash("RUT inválido", "danger")
            return render_template("register.html")

        if len(nombre.split()) < 2:
            flash("Ingrese nombre y apellido completos", "danger")
            return render_template("register.html")

        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', correo):
            flash("Formato de correo electrónico inválido", "danger")
            return render_template("register.html")

        if len(pwd) < 6:
            flash("La contraseña debe tener al menos 6 caracteres", "danger")
            return render_template("register.html")

        if pwd != cpwd:
            flash("Las contraseñas no coinciden", "danger")
            return render_template("register.html")

        ok, msg = crear_usuario(rut, nombre, correo, pwd)
        flash(msg, "success" if ok else "danger")
        if ok:
            flash("Ya puedes iniciar sesión con tus credenciales", "info")
            return redirect(url_for("auth.login"))

    return render_template("register.html")

@bp_auth.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión exitosamente", "info")
    return redirect(url_for("auth.login"))
