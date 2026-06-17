"""
routes/rfid_routes.py
=======================
Blueprint que expone la API consumida por el ESP32.

Mejoras respecto al original:
  - Siempre responde JSON consistente con status / message / timestamp
    (el original mezclaba texto plano como "OK", "IGNORADO", etc.).
  - Valida un header opcional X-API-Key para que solo el dispositivo
    autorizado pueda registrar asistencias (el original aceptaba
    cualquier POST de cualquier origen).
  - El envio del mensaje de Telegram se hace en un hilo en segundo
    plano: el ESP32 recibe la respuesta de inmediato sin esperar a que
    Telegram responda (hasta 3 reintentos x 5s podian bloquear el
    request original).
"""

import logging
import threading
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from models import attendance, student
from services.telegram_service import TelegramService

logger = logging.getLogger("asistencia")

bp = Blueprint("rfid", __name__)


def _respuesta(status: str, message: str, http_status: int, timestamp: str = None) -> tuple:
    """Construye una respuesta JSON consistente para el dispositivo ESP32."""
    return (
        jsonify(
            status=status,
            message=message,
            timestamp=timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
        http_status,
    )


def _api_key_valida() -> bool:
    """
    Verifica el header X-API-Key contra RFID_API_KEY.
    Si RFID_API_KEY no esta configurada, se permite el acceso (modo
    compatible con instalaciones que aun no actualizaron el firmware
    del ESP32) pero ya se registro una advertencia al iniciar la app.
    """
    clave_esperada = current_app.config.get("RFID_API_KEY", "")
    if not clave_esperada:
        return True
    return request.headers.get("X-API-Key", "") == clave_esperada


def _notificar_telegram_en_segundo_plano(
    telegram_service: TelegramService,
    chat_id: str,
    nombre: str,
    evento: str,
    momento: datetime,
) -> None:
    """Envia la notificacion de Telegram en un hilo separado del request."""
    mensaje = (
        "📚 SISTEMA DE ASISTENCIA\n\n"
        f"Alumno: {nombre}\n"
        f"Evento: {evento}\n"
        f"Fecha: {momento.strftime('%d/%m/%Y')}\n"
        f"Hora: {momento.strftime('%H:%M:%S')}"
    )
    hilo = threading.Thread(
        target=telegram_service.enviar_mensaje,
        args=(chat_id, mensaje),
        daemon=True,
    )
    hilo.start()


@bp.route("/dato", methods=["POST"])
def recibir_dato():
    """Recibe la lectura de una tarjeta RFID desde el ESP32 y registra el marcaje."""

    if not _api_key_valida():
        logger.warning("Intento de acceso a /dato con API key invalida o ausente.")
        return _respuesta("error", "No autorizado.", 401)

    datos = request.get_json(silent=True)
    if not datos:
        return _respuesta("error", "Cuerpo JSON invalido o vacio.", 400)

    uid = str(datos.get("uid", "")).strip().upper()
    if not uid:
        return _respuesta("error", "El campo 'uid' es obligatorio.", 400)

    estudiante = student.obtener_por_uid(uid)
    if estudiante is None:
        logger.warning("UID no registrado recibido desde el ESP32: %s", uid)
        return _respuesta("error", "UID no registrado.", 404)

    tiempo_bloqueo = current_app.config["TIEMPO_BLOQUEO"]
    ultimo = attendance.obtener_ultimo_evento(uid)

    if ultimo is not None:
        diferencia = (datetime.now() - ultimo.fecha_hora).total_seconds()
        if diferencia < tiempo_bloqueo:
            logger.info(
                "Lectura ignorada para uid=%s (%.1fs desde el ultimo marcaje, limite=%ss).",
                uid, diferencia, tiempo_bloqueo,
            )
            return _respuesta(
                "ignorado",
                f"Lectura ignorada: deben pasar {tiempo_bloqueo} segundos entre marcajes.",
                429,
            )
        evento = "SALIDA" if ultimo.evento == "ENTRADA" else "ENTRADA"
    else:
        evento = "ENTRADA"

    momento = attendance.registrar(uid, estudiante.nombre, evento)

    if estudiante.telegram_chat_id:
        _notificar_telegram_en_segundo_plano(
            current_app.extensions["telegram_service"],
            estudiante.telegram_chat_id,
            estudiante.nombre,
            evento,
            momento,
        )

    logger.info(
        "Asistencia registrada: uid=%s nombre=%s evento=%s",
        uid, estudiante.nombre, evento,
    )

    return _respuesta(
        "success",
        f"{evento.capitalize()} registrada correctamente para {estudiante.nombre}.",
        200,
        timestamp=momento.strftime("%Y-%m-%d %H:%M:%S"),
    )
