"""
routes/dashboard_routes.py
============================
Blueprint del panel de asistencias.

La pagina /dashboard solo entrega el "esqueleto" HTML. Las tarjetas de
estadisticas, la tabla (DataTables) y los graficos (Chart.js) se
llenan despues mediante peticiones AJAX a los endpoints /api/* de este
mismo blueprint. Esto separa presentacion de datos y permite refrescar
cada pieza de forma independiente sin recargar la pagina completa.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request

from models import attendance, student

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

FILTROS_VALIDOS = {"dia", "semana", "mes"}


def _calcular_rango(filtro: str) -> tuple[datetime, str]:
    """Traduce el filtro ('dia'/'semana'/'mes') a una fecha de inicio y una etiqueta legible."""
    ahora = datetime.now()

    if filtro == "semana":
        desde = ahora - timedelta(days=7)
        etiqueta = f"Ultimos 7 dias ({desde.strftime('%d/%m/%Y')} - {ahora.strftime('%d/%m/%Y')})"
    elif filtro == "mes":
        desde = ahora - timedelta(days=30)
        etiqueta = f"Ultimos 30 dias ({desde.strftime('%d/%m/%Y')} - {ahora.strftime('%d/%m/%Y')})"
    else:
        filtro = "dia"
        desde = ahora - timedelta(days=1)
        etiqueta = f"Ultimas 24 horas ({desde.strftime('%d/%m/%Y %H:%M')} - {ahora.strftime('%d/%m/%Y %H:%M')})"

    return desde, etiqueta


@bp.route("/")
def panel():
    """Renderiza el esqueleto del dashboard; los datos llegan via AJAX."""
    filtro = request.args.get("filtro", "dia")
    if filtro not in FILTROS_VALIDOS:
        filtro = "dia"

    _, etiqueta_rango = _calcular_rango(filtro)
    return render_template("dashboard.html", filtro_actual=filtro, etiqueta_rango=etiqueta_rango)


@bp.route("/api/resumen")
def api_resumen():
    """Tarjetas informativas: totales y ultimos eventos."""
    ahora = datetime.now()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    ultimo_est = student.ultimo_registrado()
    ultimo_acc = attendance.ultimo_acceso()

    return jsonify(
        total_estudiantes=student.contar_total(),
        entradas_hoy=attendance.contar_evento_desde("ENTRADA", inicio_hoy),
        salidas_hoy=attendance.contar_evento_desde("SALIDA", inicio_hoy),
        ultimo_estudiante=(
            {"nombre": ultimo_est.nombre, "uid": ultimo_est.uid} if ultimo_est else None
        ),
        ultimo_acceso=ultimo_acc,
    )


@bp.route("/api/asistencias")
def api_asistencias():
    """Datos crudos para la tabla DataTables, segun el filtro de rango."""
    filtro = request.args.get("filtro", "dia")
    if filtro not in FILTROS_VALIDOS:
        filtro = "dia"

    desde, etiqueta_rango = _calcular_rango(filtro)
    datos = attendance.listar_en_rango(desde)

    return jsonify(rango=etiqueta_rango, data=datos)


@bp.route("/api/graficos")
def api_graficos():
    """
    Series para los 4 graficos de Chart.js solicitados:
    entradas por dia, salidas por dia, asistencias semanales y mensuales.
    Se entregan en una sola respuesta para minimizar peticiones al cargar
    el dashboard.
    """
    return jsonify(
        entradas_diarias=attendance.serie_diaria("ENTRADA", dias=7),
        salidas_diarias=attendance.serie_diaria("SALIDA", dias=7),
        semanal=attendance.serie_semanal(semanas=8),
        mensual=attendance.serie_mensual(meses=6),
    )
