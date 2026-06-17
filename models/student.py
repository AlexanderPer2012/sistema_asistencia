"""
models/student.py
==================
Capa de acceso a datos para la tabla `estudiantes`.

Siguiendo el principio de responsabilidad unica (S de SOLID), este
modulo es el UNICO lugar del proyecto que sabe escribir SQL sobre la
tabla `estudiantes`. Las rutas (routes/) nunca ejecutan SQL
directamente: solo llaman a estas funciones.
"""

from dataclasses import dataclass
from typing import Optional
import sqlite3

from database.db import get_db


@dataclass(frozen=True)
class Estudiante:
    """Representa una fila de la tabla `estudiantes`."""
    uid: str
    nombre: str
    telegram_chat_id: Optional[str]
    creado_en: Optional[str] = None

    @staticmethod
    def desde_fila(fila: sqlite3.Row) -> "Estudiante":
        return Estudiante(
            uid=fila["uid"],
            nombre=fila["nombre"],
            telegram_chat_id=fila["telegram_chat_id"],
            creado_en=fila["creado_en"] if "creado_en" in fila.keys() else None,
        )


def obtener_por_uid(uid: str) -> Optional[Estudiante]:
    """Busca un estudiante por su UID de tarjeta RFID."""
    fila = get_db().execute(
        "SELECT uid, nombre, telegram_chat_id, creado_en "
        "FROM estudiantes WHERE uid = ?",
        (uid,),
    ).fetchone()
    return Estudiante.desde_fila(fila) if fila else None


def guardar(uid: str, nombre: str, telegram_chat_id: str) -> None:
    """
    Crea un estudiante nuevo o actualiza uno existente.

    Mejora sobre el original: se usa `INSERT ... ON CONFLICT DO UPDATE`
    en vez de `INSERT OR REPLACE`. `INSERT OR REPLACE` borra la fila
    completa y la vuelve a crear, lo que pondria en NULL cualquier
    columna futura que no se incluya explicitamente en el INSERT (por
    ejemplo, si en el futuro se agrega una columna "grado" y el
    formulario de edicion no la envia, REPLACE la perderia). El UPSERT
    solo modifica las columnas indicadas y conserva el resto.
    """
    get_db().execute(
        """
        INSERT INTO estudiantes (uid, nombre, telegram_chat_id)
        VALUES (?, ?, ?)
        ON CONFLICT (uid) DO UPDATE SET
            nombre = excluded.nombre,
            telegram_chat_id = excluded.telegram_chat_id
        """,
        (uid, nombre, telegram_chat_id),
    )
    get_db().commit()


def eliminar_por_uid(uid: str) -> bool:
    """Elimina un estudiante por UID. Devuelve True si existia."""
    cursor = get_db().execute(
        "DELETE FROM estudiantes WHERE uid = ?", (uid,)
    )
    get_db().commit()
    return cursor.rowcount > 0


def listar_todos() -> list[Estudiante]:
    """Devuelve todos los estudiantes ordenados por nombre."""
    filas = get_db().execute(
        "SELECT uid, nombre, telegram_chat_id, creado_en "
        "FROM estudiantes ORDER BY nombre COLLATE NOCASE"
    ).fetchall()
    return [Estudiante.desde_fila(fila) for fila in filas]


def contar_total() -> int:
    """Cantidad total de estudiantes registrados (para tarjetas del dashboard)."""
    fila = get_db().execute("SELECT COUNT(*) AS total FROM estudiantes").fetchone()
    return fila["total"]


def ultimo_registrado() -> Optional[Estudiante]:
    """Estudiante mas reciente agregado al sistema."""
    fila = get_db().execute(
        "SELECT uid, nombre, telegram_chat_id, creado_en "
        "FROM estudiantes ORDER BY creado_en DESC, uid DESC LIMIT 1"
    ).fetchone()
    return Estudiante.desde_fila(fila) if fila else None
