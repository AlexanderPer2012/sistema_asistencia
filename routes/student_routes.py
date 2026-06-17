"""
routes/student_routes.py
==========================
Blueprint para la gestion de estudiantes: alta, baja y listado.

Cambios de seguridad relevantes respecto al original:
  - El registro usa EstudianteForm (validacion + CSRF).
  - La eliminacion pasa de un enlace GET (/borrar/<uid>) a un POST
    protegido con CSRF, confirmado en el navegador con SweetAlert2
    antes de enviarse. Un GET nunca deberia provocar un cambio de
    estado: el enlace original era vulnerable a CSRF y a borrados
    accidentales por precarga del navegador.
"""

import logging

from flask import Blueprint, jsonify, render_template, request

from forms import EliminarEstudianteForm, EstudianteForm
from models import student

logger = logging.getLogger("asistencia")

bp = Blueprint("students", __name__)


@bp.route("/agregar", methods=["GET", "POST"])
def agregar():
    """Formulario de alta/actualizacion de estudiantes."""
    form = EstudianteForm()

    if form.validate_on_submit():
        uid = form.uid.data.strip().upper()
        nombre = form.nombre.data.strip()
        chat_id = (form.chat_id.data or "").strip()

        student.guardar(uid=uid, nombre=nombre, telegram_chat_id=chat_id)
        logger.info("Estudiante guardado: uid=%s nombre=%s", uid, nombre)

        return jsonify(
            status="success",
            message=f"Estudiante '{nombre}' guardado correctamente.",
        )

    if form.errors:
        # Devuelve el primer error de validacion de forma legible
        # para que SweetAlert2 lo muestre en el formulario.
        primer_error = next(iter(form.errors.values()))[0]
        return jsonify(status="error", message=primer_error), 400

    return render_template("agregar.html", form=form)


@bp.route("/eliminar")
def eliminar():
    """Lista de estudiantes con opcion de eliminar cada uno."""
    estudiantes = student.listar_todos()
    form = EliminarEstudianteForm()
    return render_template("eliminar.html", estudiantes=estudiantes, form=form)


@bp.route("/borrar/<uid>", methods=["POST"])
def borrar(uid: str):
    """
    Elimina un estudiante por UID.

    Requiere POST (con token CSRF valido) en vez de GET, y se invoca
    desde el navegador solo despues de una confirmacion explicita con
    SweetAlert2 (ver static/js/eliminar.js).
    """
    form = EliminarEstudianteForm()

    if not form.validate_on_submit():
        return jsonify(status="error", message="Token de seguridad invalido."), 400

    uid_normalizado = uid.strip().upper()
    eliminado = student.eliminar_por_uid(uid_normalizado)

    if not eliminado:
        return jsonify(status="error", message="El estudiante no existe."), 404

    logger.info("Estudiante eliminado: uid=%s", uid_normalizado)
    return jsonify(status="success", message="Estudiante eliminado correctamente.")
