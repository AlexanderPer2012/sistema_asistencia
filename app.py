"""
app.py
======
Punto de entrada de la aplicacion. Usa el patron "application factory"
(create_app) en vez de un modulo Flask global: esto facilita las
pruebas automatizadas (se puede crear una app nueva con configuracion
distinta por cada test) y evita efectos secundarios de import.

Para desarrollo local:
    flask --app app run --debug

Para produccion, no se usa app.run(): ver README.md para el comando
recomendado con waitress/gunicorn detras de un proxy como Nginx.
"""

import logging

from flask import Flask
from flask_wtf import CSRFProtect

from config import obtener_configuracion
from database.db import inicializar_bd
from services.logger_service import configurar_logging
from services.telegram_service import TelegramService

csrf = CSRFProtect()


def create_app(config_class=None) -> Flask:
    """Crea y configura la instancia de Flask."""
    app = Flask(__name__)
    app.config.from_object(config_class or obtener_configuracion())

    # Si no hay SECRET_KEY configurada en .env, se genera una temporal
    # en memoria para que la app pueda arrancar en desarrollo. Esto
    # invalida sesiones/CSRF al reiniciar, por lo que en produccion
    # SIEMPRE debe definirse SECRET_KEY en el archivo .env.
    if not app.config.get("SECRET_KEY"):
        import secrets
        app.config["SECRET_KEY"] = secrets.token_hex(32)

    # -------------------------------------------------------------
    # Logging (antes que cualquier otra cosa, para poder registrar
    # las advertencias de configuracion que siguen).
    # -------------------------------------------------------------
    logger = configurar_logging(app)

    config_actual = config_class or obtener_configuracion()
    for advertencia in config_actual.validar():
        logger.warning(advertencia)

    # -------------------------------------------------------------
    # Extensiones
    # -------------------------------------------------------------
    csrf.init_app(app)

    app.extensions["telegram_service"] = TelegramService(
        token=app.config["TELEGRAM_TOKEN"],
        timeout=app.config["TELEGRAM_TIMEOUT"],
        max_reintentos=app.config["TELEGRAM_MAX_REINTENTOS"],
        espera_reintento=app.config["TELEGRAM_ESPERA_REINTENTO"],
    )

    # -------------------------------------------------------------
    # Base de datos
    # -------------------------------------------------------------
    inicializar_bd(app)

    # -------------------------------------------------------------
    # Blueprints
    # -------------------------------------------------------------
    from routes.main_routes import bp as main_bp
    from routes.student_routes import bp as students_bp
    from routes.dashboard_routes import bp as dashboard_bp
    from routes.rfid_routes import bp as rfid_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(rfid_bp)

    # El endpoint /dato lo consume un dispositivo IoT (ESP32), no un
    # navegador con sesion/cookies: el concepto de CSRF no aplica ahi.
    # Se protege en su lugar con el header X-API-Key (ver
    # routes/rfid_routes.py y RFID_API_KEY en config.py).
    csrf.exempt(rfid_bp)

    logger.info("Aplicacion inicializada correctamente.")
    return app


if __name__ == "__main__":
    aplicacion = create_app()
    aplicacion.run(
        host=aplicacion.config["HOST"],
        port=aplicacion.config["PORT"],
        debug=aplicacion.config["DEBUG"],
    )
