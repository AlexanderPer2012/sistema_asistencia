"""
models/attendance.py
=====================
Capa de acceso a datos para la tabla `asistencias`.

Concentra toda la logica SQL relacionada con marcajes de entrada y
salida: el registro que llega del ESP32, la tabla del dashboard y las
series usadas por los graficos de Chart.js.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from database.db import get_db


@dataclass(frozen=True)
class UltimoEvento:
    """Ultimo evento (ENTRADA/SALIDA) registrado para un UID."""
    evento: str
    fecha_hora: datetime


def obtener_ultimo_evento(uid: str) -> Optional[UltimoEvento]:
    """
    Devuelve el ultimo evento registrado para un UID, o None si la
    tarjeta nunca se ha marcado.
    """
    fila = get_db().execute(
        """
        SELECT evento, fecha_hora FROM asistencias
        WHERE uid = ? ORDER BY id DESC LIMIT 1
        """,
        (uid,),
    ).fetchone()

    if fila is None:
        return None

    try:
        fecha = datetime.strptime(fila["fecha_hora"], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        # Si la fecha almacenada esta corrupta no se debe tumbar el
        # request entero (el codigo original no manejaba este caso):
        # se trata como si no hubiera historial previo, priorizando
        # disponibilidad sobre el bloqueo de duplicados.
        return None

    return UltimoEvento(evento=fila["evento"], fecha_hora=fecha)


def registrar(uid: str, nombre: str, evento: str) -> datetime:
    """Inserta un nuevo marcaje de asistencia y devuelve su timestamp."""
    ahora = datetime.now()
    get_db().execute(
        """
        INSERT INTO asistencias (uid, nombre, evento, fecha_hora)
        VALUES (?, ?, ?, ?)
        """,
        (uid, nombre, evento, ahora.strftime("%Y-%m-%d %H:%M:%S")),
    )
    get_db().commit()
    return ahora


def listar_en_rango(desde: datetime) -> list[dict]:
    """Lista de marcajes desde una fecha, para alimentar la tabla del dashboard."""
    filas = get_db().execute(
        """
        SELECT uid, nombre, evento, fecha_hora FROM asistencias
        WHERE fecha_hora >= ?
        ORDER BY id DESC
        """,
        (desde.strftime("%Y-%m-%d %H:%M:%S"),),
    ).fetchall()
    return [dict(fila) for fila in filas]


def contar_evento_desde(evento: str, desde: datetime) -> int:
    """Cuenta cuantos eventos de un tipo ocurrieron desde una fecha (p. ej. 'hoy')."""
    fila = get_db().execute(
        """
        SELECT COUNT(*) AS total FROM asistencias
        WHERE evento = ? AND fecha_hora >= ?
        """,
        (evento, desde.strftime("%Y-%m-%d %H:%M:%S")),
    ).fetchone()
    return fila["total"]


def ultimo_acceso() -> Optional[dict]:
    """Ultimo marcaje registrado en todo el sistema (cualquier estudiante)."""
    fila = get_db().execute(
        """
        SELECT uid, nombre, evento, fecha_hora FROM asistencias
        ORDER BY id DESC LIMIT 1
        """
    ).fetchone()
    return dict(fila) if fila else None


def serie_diaria(evento: str, dias: int = 7) -> list[dict]:
    """
    Total de un tipo de evento por dia, en los ultimos `dias` dias
    (incluye hoy). Los dias sin registros se devuelven con total 0
    para que el grafico de Chart.js no tenga huecos.
    """
    hoy = datetime.now().date()
    inicio = hoy - timedelta(days=dias - 1)

    filas = get_db().execute(
        """
        SELECT substr(fecha_hora, 1, 10) AS dia, COUNT(*) AS total
        FROM asistencias
        WHERE evento = ? AND fecha_hora >= ?
        GROUP BY dia
        """,
        (evento, inicio.strftime("%Y-%m-%d 00:00:00")),
    ).fetchall()

    conteo_por_dia = {fila["dia"]: fila["total"] for fila in filas}

    return [
        {
            "fecha": (inicio + timedelta(days=i)).strftime("%Y-%m-%d"),
            "total": conteo_por_dia.get((inicio + timedelta(days=i)).strftime("%Y-%m-%d"), 0),
        }
        for i in range(dias)
    ]


def serie_semanal(semanas: int = 8) -> list[dict]:
    """
    Total de asistencias (entradas + salidas) por semana de lunes a
    domingo, en las ultimas `semanas` semanas. Cada bucket se calcula
    en Python y se consulta por separado; con N pequeno (8-12) el
    costo es minimo gracias al indice sobre fecha_hora.
    """
    hoy = datetime.now().date()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    db = get_db()
    resultado = []

    for i in range(semanas - 1, -1, -1):
        inicio_semana = lunes_actual - timedelta(weeks=i)
        fin_semana = inicio_semana + timedelta(days=7)

        fila = db.execute(
            """
            SELECT COUNT(*) AS total FROM asistencias
            WHERE fecha_hora >= ? AND fecha_hora < ?
            """,
            (
                inicio_semana.strftime("%Y-%m-%d 00:00:00"),
                fin_semana.strftime("%Y-%m-%d 00:00:00"),
            ),
        ).fetchone()

        resultado.append({
            "semana": f"{inicio_semana.strftime('%d/%m')}",
            "total": fila["total"],
        })

    return resultado


def serie_mensual(meses: int = 6) -> list[dict]:
    """Total de asistencias por mes calendario, en los ultimos `meses` meses."""
    hoy = datetime.now().date()
    db = get_db()

    primeros_dias = []
    cursor_fecha = hoy.replace(day=1)
    for _ in range(meses):
        primeros_dias.append(cursor_fecha)
        cursor_fecha = (cursor_fecha - timedelta(days=1)).replace(day=1)
    primeros_dias.reverse()

    resultado = []
    for indice, inicio_mes in enumerate(primeros_dias):
        if indice + 1 < len(primeros_dias):
            fin_mes = primeros_dias[indice + 1]
        elif inicio_mes.month == 12:
            fin_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fin_mes = inicio_mes.replace(month=inicio_mes.month + 1)

        fila = db.execute(
            """
            SELECT COUNT(*) AS total FROM asistencias
            WHERE fecha_hora >= ? AND fecha_hora < ?
            """,
            (
                inicio_mes.strftime("%Y-%m-%d 00:00:00"),
                fin_mes.strftime("%Y-%m-%d 00:00:00"),
            ),
        ).fetchone()

        resultado.append({
            "mes": inicio_mes.strftime("%m/%Y"),
            "total": fila["total"],
        })

    return resultado
