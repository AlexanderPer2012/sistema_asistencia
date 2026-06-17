"""
services/telegram_service.py
==============================
Modulo independiente para el envio de notificaciones por Telegram.

Mejoras sobre el original:
  - Reintentos automaticos con espera incremental si la peticion falla
    (timeout, error de red, error 5xx de la API de Telegram).
  - Errores registrados con el logger central en vez de `print()`.
  - El token se recibe por configuracion (en vez de estar escrito en
    el codigo), y la clase puede deshabilitarse limpiamente si no hay
    token configurado, sin que el resto de la aplicacion se entere.
"""

import logging
import time

import requests

logger = logging.getLogger("asistencia")


class TelegramService:
    """Cliente sencillo para enviar mensajes de texto a un chat de Telegram."""

    def __init__(
        self,
        token: str,
        timeout: float = 5.0,
        max_reintentos: int = 3,
        espera_reintento: float = 1.5,
    ) -> None:
        self._token = token
        self._timeout = timeout
        self._max_reintentos = max(1, max_reintentos)
        self._espera_reintento = espera_reintento
        self._habilitado = bool(token)

        if not self._habilitado:
            logger.warning(
                "TelegramService inicializado sin token: las notificaciones "
                "quedan deshabilitadas hasta que se configure TELEGRAM_TOKEN."
            )

    @property
    def habilitado(self) -> bool:
        return self._habilitado

    def enviar_mensaje(self, chat_id: str, mensaje: str) -> bool:
        """
        Envia un mensaje de texto a un chat_id de Telegram.

        Reintenta hasta `max_reintentos` veces con espera incremental
        (backoff lineal) ante fallas de red o respuestas de error del
        servidor. Devuelve True si el mensaje se envio correctamente,
        False en caso contrario (nunca lanza una excepcion hacia quien
        la llama, para no interrumpir el flujo de registro de
        asistencia por un problema de Telegram).
        """
        if not self._habilitado:
            logger.debug("Envio de Telegram omitido: servicio deshabilitado.")
            return False

        if not chat_id:
            logger.debug("Envio de Telegram omitido: chat_id vacio.")
            return False

        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mensaje}

        for intento in range(1, self._max_reintentos + 1):
            try:
                respuesta = requests.post(url, data=payload, timeout=self._timeout)

                if respuesta.status_code == 200:
                    logger.info("Mensaje de Telegram enviado a chat_id=%s", chat_id)
                    return True

                logger.warning(
                    "Telegram respondio con estado %s en el intento %s/%s: %s",
                    respuesta.status_code,
                    intento,
                    self._max_reintentos,
                    respuesta.text[:200],
                )

            except requests.exceptions.RequestException as error:
                logger.warning(
                    "Error de red enviando Telegram (intento %s/%s): %s",
                    intento,
                    self._max_reintentos,
                    error,
                )

            if intento < self._max_reintentos:
                time.sleep(self._espera_reintento * intento)

        logger.error(
            "No se pudo enviar el mensaje de Telegram a chat_id=%s tras %s intentos.",
            chat_id,
            self._max_reintentos,
        )
        return False
