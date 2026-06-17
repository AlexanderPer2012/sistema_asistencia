"""
forms.py
========
Formularios basados en Flask-WTF.

Usar WTForms en vez de leer `request.form[...]` directamente (como en
el codigo original) aporta dos mejoras de seguridad importantes:

  1. Validacion de entradas: tipo, longitud y formato se verifican
     antes de tocar la base de datos (el original guardaba cualquier
     valor sin revisar nada).
  2. Proteccion CSRF automatica: Flask-WTF incluye un token oculto en
     cada formulario y lo valida en el servidor.
"""

from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length, Regexp, Optional as OptionalField


class EstudianteForm(FlaskForm):
    """Formulario para registrar o actualizar un estudiante."""

    uid = StringField(
        "UID de la tarjeta",
        validators=[
            DataRequired(message="El UID es obligatorio."),
            Length(min=4, max=32, message="El UID debe tener entre 4 y 32 caracteres."),
            Regexp(
                r"^[A-Za-z0-9:_-]+$",
                message="El UID solo puede contener letras, numeros, guiones y dos puntos.",
            ),
        ],
    )

    nombre = StringField(
        "Nombre completo",
        validators=[
            DataRequired(message="El nombre es obligatorio."),
            Length(min=2, max=120, message="El nombre debe tener entre 2 y 120 caracteres."),
        ],
    )

    chat_id = StringField(
        "Telegram Chat ID",
        validators=[
            OptionalField(),
            Regexp(
                r"^-?\d+$",
                message="El Chat ID de Telegram debe ser numerico (puede iniciar con '-').",
            ),
        ],
    )


class EliminarEstudianteForm(FlaskForm):
    """
    Formulario vacio que solo existe para llevar el token CSRF de la
    accion de eliminar. Reemplaza el enlace GET /borrar/<uid> original
    (que ejecutaba un borrado con un simple click o incluso con un
    prefetch del navegador) por un POST protegido contra CSRF.
    """
    pass
