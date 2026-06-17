"""
database/db.py
===============
Gestion de la conexion a SQLite.

Mejora de rendimiento clave respecto al codigo original: en lugar de
abrir y cerrar una conexion nueva en cada consulta (sqlite3.connect /
conexion.close repetidos varias veces dentro de un mismo request), se
usa el patron oficial de Flask basado en el objeto `g`:

  - get_db() abre la conexion UNA sola vez por request y la reutiliza
    para todas las consultas de ese request.
  - cerrar_conexion() se registra con `app.teardown_appcontext` y cierra
    la conexion automaticamente al finalizar el request, incluso si
    ocurre una excepcion (algo que el codigo original no garantizaba).
"""

import sqlite3
import logging
from pathlib import Path

from flask import g, current_app

logger = logging.getLogger("asistencia")


def get_db() -> sqlite3.Connection:
    """
    Devuelve la conexion SQLite asociada al contexto de la peticion
    actual. Si no existe todavia, la crea y la guarda en `g` para que
    las siguientes llamadas dentro del mismo request reutilicen la
    misma conexion en lugar de abrir una nueva.
    """
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        # row_factory permite acceder a columnas por nombre (fila["uid"])
        # en vez de solo por indice posicional, mejorando la legibilidad.
        g.db.row_factory = sqlite3.Row
        # Habilita las llaves foraneas (SQLite las trae desactivadas
        # por defecto) para mantener integridad referencial entre
        # asistencias.uid y estudiantes.uid.
        g.db.execute("PRAGMA foreign_keys = ON")
        # WAL mejora la concurrencia entre lecturas y escrituras,
        # relevante cuando varios ESP32 escriben mientras el dashboard lee.
        g.db.execute("PRAGMA journal_mode = WAL")

    return g.db


def cerrar_conexion(excepcion=None) -> None:
    """Cierra la conexion de la peticion actual, si fue abierta."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def inicializar_bd(app) -> None:
    """
    Crea las tablas e indices si no existen todavia y registra el
    cierre automatico de la conexion al finalizar cada peticion.

    Se llama una sola vez, durante la creacion de la aplicacion
    (create_app), no en cada peticion.
    """
    db_path = Path(app.config["DATABASE_PATH"])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conexion = sqlite3.connect(app.config["DATABASE_PATH"])
    conexion.execute("PRAGMA foreign_keys = ON")
    cursor = conexion.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudiantes (
            uid TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            telegram_chat_id TEXT,
            creado_en TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS asistencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT,
            -- 'uid' es NULLABLE a proposito: si el estudiante se elimina
            -- mas adelante, ON DELETE SET NULL deja el historico intacto
            -- (el campo 'nombre' ya esta desnormalizado abajo para que
            -- la fila siga siendo legible aunque uid quede en NULL).
            nombre TEXT NOT NULL,
            evento TEXT NOT NULL CHECK (evento IN ('ENTRADA', 'SALIDA')),
            fecha_hora TEXT NOT NULL,
            FOREIGN KEY (uid) REFERENCES estudiantes (uid) ON DELETE SET NULL
        )
        """
    )

    # -----------------------------------------------------------------
    # Indices: el codigo original no tenia ninguno mas alla de la llave
    # primaria de "estudiantes". Estas consultas se ejecutan en cada
    # lectura de tarjeta y en cada carga del dashboard, asi que sin
    # indice degradan a un escaneo completo de tabla a medida que crece
    # el historico de asistencias.
    # -----------------------------------------------------------------

    # Acelera "ultimo registro de este uid" (ORDER BY id DESC WHERE uid=?)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_asistencias_uid ON asistencias (uid)"
    )

    # Acelera los filtros del dashboard (WHERE fecha_hora >= ?)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_asistencias_fecha_hora "
        "ON asistencias (fecha_hora)"
    )

    # Indice compuesto para la consulta mas frecuente: "el ultimo
    # evento de este uid" combinada con orden por fecha.
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_asistencias_uid_fecha "
        "ON asistencias (uid, fecha_hora DESC)"
    )

    # Acelera agregaciones del dashboard por tipo de evento.
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_asistencias_evento "
        "ON asistencias (evento)"
    )

    conexion.commit()
    conexion.close()

    # Registra el cierre automatico de la conexion al final de cada
    # contexto de aplicacion (cada peticion HTTP).
    app.teardown_appcontext(cerrar_conexion)

    logger.info("Base de datos inicializada en %s", app.config["DATABASE_PATH"])
