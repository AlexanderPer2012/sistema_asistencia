"""
services/logger_service.py
============================
Configuracion centralizada de logging.

El codigo original usaba `print()` para todo: errores de Telegram,
UIDs no registrados, intentos ignorados, etc. Eso significa que en
produccion (detras de un servidor WSGI) esos mensajes se pierden o
quedan mezclados en stdout sin nivel de severidad, sin fecha y sin
posibilidad de revisarlos despues de un reinicio.

Este modulo configura un logger con:
  - Salida a archivo rotativo (no crece sin limite).
  - Salida a consola (para `flask run` / desarrollo).
  - Formato consistente con fecha, nivel y modulo de origen.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configurar_logging(app) -> logging.Logger:
    """Configura el logger 'asistencia' usado en toda la aplicacion."""

    log_dir = Path(app.config["LOG_DIR"])
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / app.config["LOG_FILE"]

    logger = logging.getLogger("asistencia")
    logger.setLevel(app.config["LOG_LEVEL"])

    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Archivo rotativo: maximo 1 MB por archivo, conserva 5 archivos
    # antiguos antes de descartar el mas viejo.
    manejador_archivo = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    manejador_archivo.setFormatter(formato)

    manejador_consola = logging.StreamHandler()
    manejador_consola.setFormatter(formato)

    # Evita duplicar manejadores si la app se crea mas de una vez
    # (por ejemplo, durante pruebas automatizadas).
    if not logger.handlers:
        logger.addHandler(manejador_archivo)
        logger.addHandler(manejador_consola)

    # Tambien se conecta el logger propio de Flask al mismo formato,
    # para que los errores internos (404, 500, etc.) queden en el
    # mismo archivo.
    app.logger.handlers = logger.handlers
    app.logger.setLevel(app.config["LOG_LEVEL"])

    return logger
