"""
config.py
=========
Configuracion centralizada de la aplicacion.

Todos los valores sensibles o dependientes del entorno (tokens, rutas,
puertos, tiempos) se leen desde variables de entorno (archivo .env) en
lugar de estar escritos directamente en el codigo fuente. Esto evita
exponer credenciales en el control de versiones y permite usar
configuraciones distintas en desarrollo, pruebas y produccion.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carga el archivo .env ubicado en la raiz del proyecto (si existe).
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


def _str_to_bool(valor: str) -> bool:
    """Convierte un string de variable de entorno a booleano de forma segura."""
    return str(valor).strip().lower() in ("1", "true", "yes", "on")


class Config:
    """
    Configuracion base de la aplicacion Flask.

    Todos los atributos se exponen como mayusculas para seguir la
    convencion que Flask espera en `app.config`.
    """

    # -------------------------------------------------------------
    # Seguridad
    # -------------------------------------------------------------
    # Clave secreta usada por Flask para firmar la sesion y por
    # Flask-WTF para generar/validar los tokens CSRF.
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")

    # Clave compartida opcional que el ESP32 debe enviar en el header
    # "X-API-Key" al consumir el endpoint /dato. Si se deja vacia,
    # el endpoint queda abierto (no recomendado en produccion) pero se
    # registra una advertencia en el log al iniciar la aplicacion.
    RFID_API_KEY: str = os.getenv("RFID_API_KEY", "")

    # -------------------------------------------------------------
    # Telegram
    # -------------------------------------------------------------
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_TIMEOUT: float = float(os.getenv("TELEGRAM_TIMEOUT", "5"))
    TELEGRAM_MAX_REINTENTOS: int = int(os.getenv("TELEGRAM_MAX_REINTENTOS", "3"))
    TELEGRAM_ESPERA_REINTENTO: float = float(os.getenv("TELEGRAM_ESPERA_REINTENTO", "1.5"))

    # -------------------------------------------------------------
    # Reglas de negocio
    # -------------------------------------------------------------
    # Tiempo (segundos) durante el cual se ignoran lecturas repetidas
    # de la misma tarjeta para evitar registros duplicados.
    TIEMPO_BLOQUEO: int = int(os.getenv("TIEMPO_BLOQUEO", "60"))

    # -------------------------------------------------------------
    # Base de datos
    # -------------------------------------------------------------
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", str(BASE_DIR / "database" / "asistencia.db")
    )

    # -------------------------------------------------------------
    # Servidor
    # -------------------------------------------------------------
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = _str_to_bool(os.getenv("DEBUG", "false"))

    # -------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------
    LOG_DIR: str = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validar(cls) -> list[str]:
        """
        Revisa la configuracion critica y devuelve una lista de
        advertencias. No lanza excepciones: la aplicacion debe poder
        arrancar en un entorno de desarrollo incompleto, pero las
        advertencias quedan registradas en el log.
        """
        advertencias = []

        if not cls.SECRET_KEY:
            advertencias.append(
                "SECRET_KEY no esta definida en .env. Se usara una clave "
                "temporal generada en memoria, lo cual invalida las "
                "sesiones/CSRF cada vez que el servidor se reinicie."
            )

        if not cls.TELEGRAM_TOKEN:
            advertencias.append(
                "TELEGRAM_TOKEN no esta definido. Las notificaciones de "
                "Telegram quedaran deshabilitadas."
            )

        if not cls.RFID_API_KEY:
            advertencias.append(
                "RFID_API_KEY no esta definida. El endpoint /dato "
                "aceptara peticiones sin autenticacion de dispositivo."
            )

        if cls.DEBUG:
            advertencias.append(
                "DEBUG=true. Nunca debe usarse en produccion: expone el "
                "depurador interactivo de Werkzeug, que permite ejecutar "
                "codigo arbitrario si el servidor es alcanzable desde la red."
            )

        return advertencias


class DevelopmentConfig(Config):
    """Configuracion para entorno de desarrollo local."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuracion para entorno de produccion."""
    DEBUG = False


# Mapa usado por app.py para seleccionar la configuracion segun
# la variable de entorno FLASK_ENV.
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": ProductionConfig,
}


def obtener_configuracion() -> type[Config]:
    """Devuelve la clase de configuracion correspondiente a FLASK_ENV."""
    entorno = os.getenv("FLASK_ENV", "default")
    return CONFIG_MAP.get(entorno, ProductionConfig)
