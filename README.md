# Sistema de Asistencia RFID — Backend Flask (refactorizado)

Sistema de control de asistencia por tarjetas RFID y dispositivos ESP32,
reescrito desde un unico archivo monolitico a una arquitectura Flask
modular (Blueprints), con dashboard interactivo, exportacion de datos,
notificaciones por Telegram y proteccion CSRF.

## 1. Estructura del proyecto

```
sistema_asistencia/
├── app.py                     # Application factory (create_app)
├── config.py                  # Config / DevelopmentConfig / ProductionConfig
├── forms.py                   # Formularios Flask-WTF (validacion + CSRF)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── requirements.txt
├── database/
│   ├── db.py                  # get_db(), inicializar_bd() (tablas + indices)
│   └── __init__.py
├── models/
│   ├── student.py             # Acceso a datos: tabla `estudiantes`
│   ├── attendance.py          # Acceso a datos: tabla `asistencias` + series para graficos
│   └── __init__.py
├── routes/
│   ├── main_routes.py         # "/"
│   ├── student_routes.py      # /agregar, /eliminar, /borrar/<uid>
│   ├── dashboard_routes.py    # /dashboard y sus endpoints /api/*
│   ├── rfid_routes.py         # /dato (API consumida por el ESP32)
│   └── __init__.py
├── services/
│   ├── telegram_service.py    # Cliente de Telegram con reintentos
│   ├── logger_service.py      # Configuracion de logging a archivo
│   └── __init__.py
├── templates/
│   ├── base.html               # Layout: sidebar + navbar + CDNs
│   ├── index.html
│   ├── dashboard.html
│   ├── agregar.html
│   └── eliminar.html
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js             # Reloj + helper fetchProtegido (CSRF)
│       ├── dashboard.js        # Carga de tarjetas, graficos y DataTable
│       ├── agregar.js          # Envio AJAX del formulario de alta
│       └── eliminar.js         # Confirmacion + borrado AJAX
└── logs/                       # Se crea automaticamente (asistencia.log)
```

## 2. Puesta en marcha (desarrollo)

```bash
cd sistema_asistencia
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env y al menos define SECRET_KEY (ver paso 3)

python app.py
```

La aplicacion queda disponible en `http://127.0.0.1:5000` (o el `PORT`
que definas en `.env`). La base de datos SQLite y las tablas/indices se
crean automaticamente en el primer arranque.

## 3. Variables de entorno (`.env`)

| Variable | Obligatoria | Descripcion |
|---|---|---|
| `SECRET_KEY` | Recomendada | Firma las sesiones y los tokens CSRF. Si se omite, se genera una temporal en memoria (las sesiones se invalidan en cada reinicio). Generar con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `TELEGRAM_TOKEN` | No | Token del bot de Telegram. **El token que venia escrito en el codigo original debe considerarse comprometido**: revocalo desde `@BotFather` y genera uno nuevo antes de usar este sistema en produccion. |
| `RFID_API_KEY` | No (recomendada) | Clave que el ESP32 debe enviar en el header `X-API-Key` al llamar a `/dato`. Sin ella, el endpoint sigue funcionando (compatibilidad), pero sin autenticar el dispositivo. |
| `TIEMPO_BLOQUEO` | No | Segundos minimos entre dos marcajes de la misma tarjeta (por defecto 60). |
| `PORT`, `HOST` | No | Direccion y puerto del servidor. |
| `FLASK_ENV` | No | `development` o `production` (selecciona `DevelopmentConfig`/`ProductionConfig`). |

## 4. Despliegue en produccion

El servidor de desarrollo de Flask (`app.run`) **no** debe usarse en
produccion (es lo que ya advierte la propia consola de Flask). Se
incluye `waitress` en `requirements.txt` como servidor WSGI listo para
producción en Windows/Linux:

```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=8000 app:create_app
```

En Linux tambien es valida la alternativa con `gunicorn` detras de
Nginx como proxy inverso (terminacion TLS, compresion, archivos
estaticos):

```bash
gunicorn -w 4 -b 127.0.0.1:8000 "app:create_app()"
```

Asegurate de definir `FLASK_ENV=production` en `.env` para activar
`ProductionConfig` (debug desactivado, cookies de sesion marcadas como
`Secure`, etc.).

## 5. Mapeo de requisitos solicitados → implementacion

| # | Requisito | Donde se resolvio |
|---|---|---|
| 1 | Arquitectura con Blueprints y carpetas separadas | `app.py` (factory) + `routes/`, `models/`, `services/`, `database/` |
| 2 | Plantillas Jinja2 (sin HTML embebido) | `templates/base.html`, `index.html`, `dashboard.html`, `agregar.html`, `eliminar.html` |
| 3 | Diseño visual moderno (Bootstrap 5, sidebar, navbar, paleta solicitada) | `templates/base.html` + `static/css/style.css` |
| 4 | Dashboard avanzado (tarjetas + 4 graficos Chart.js) | `routes/dashboard_routes.py` (`/api/resumen`, `/api/graficos`) + `static/js/dashboard.js` |
| 5 | Tabla avanzada (DataTables: busqueda, orden, paginacion, exportar Excel/PDF/CSV) | `templates/dashboard.html` + `static/js/dashboard.js` (extension Buttons) |
| 6 | UX: SweetAlert2, confirmacion de borrado, animaciones | `static/js/agregar.js`, `static/js/eliminar.js`, clase `.fade-in-up` en `style.css` |
| 7 | Indices SQLite (UID, fecha_hora, consultas frecuentes) | `database/db.py` → `inicializar_bd()` |
| 8 | Seguridad: validacion, CSRF, variables de entorno | `forms.py` (Flask-WTF), `Flask-WTF CSRFProtect` en `app.py`, `.env.example` |
| 9 | `config.py`, `requirements.txt`, `.gitignore` | Raiz del proyecto |
| 10 | Reutilizar conexiones (`get_db()`, context managers) | `database/db.py` (patron `g` + `teardown_appcontext`) |
| 11 | Endpoint `/dato` con JSON consistente (`status`/`message`/`timestamp`) | `routes/rfid_routes.py` → `_respuesta()` |
| 12 | Logging profesional a archivo | `services/logger_service.py` (RotatingFileHandler) |
| 13 | Modulo independiente de Telegram con reintentos | `services/telegram_service.py` |
| 14 | SOLID, docstrings, type hints | Todos los modulos de `models/`, `services/`, `routes/` |
| 15 | Entrega completa, explicada y lista para produccion | Este README + el codigo organizado por archivo |

## 6. Limitaciones conocidas / trabajo futuro recomendado

- **Autenticacion de usuarios**: las rutas de `/agregar`, `/eliminar` y
  `/dashboard` no tienen login. El requerimiento original no lo pedia,
  pero si el panel se expone fuera de una red confiable, se recomienda
  agregar `Flask-Login` con al menos un usuario administrador antes de
  desplegarlo en internet publica.
- **Condicion de carrera en el lockout**: si dos lecturas de la misma
  tarjeta llegan en un margen de milisegundos (poco probable con un
  solo lector RFID, pero posible con varios lectores apuntando al
  mismo UID), el chequeo de "ultimo evento" no es atomico y en teoria
  podrian colarse dos marcajes. Para eliminarlo por completo haria
  falta una transaccion con bloqueo explicito o una restriccion UNICA
  a nivel de base de datos sobre una ventana de tiempo, lo cual queda
  fuera del alcance de esta refactorizacion.
- **Rotacion del token de Telegram**: el token que aparecia escrito en
  el codigo original debe tratarse como comprometido y revocarse desde
  `@BotFather`, sin importar que este proyecto ya no lo usa.
