"""
routes/main_routes.py
=======================
Blueprint con la pagina de inicio del panel.
"""

from flask import Blueprint, render_template

from models import student

bp = Blueprint("main", __name__)


@bp.route("/")
def inicio():
    """Pagina de bienvenida con accesos rapidos al resto del panel."""
    total_estudiantes = student.contar_total()
    return render_template("index.html", total_estudiantes=total_estudiantes)
