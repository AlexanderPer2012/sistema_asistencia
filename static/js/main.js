/**
 * static/js/main.js
 * Funciones compartidas por todas las paginas del panel:
 *  - Reloj en vivo en la barra superior.
 *  - Helper para incluir el token CSRF en peticiones fetch (POST/DELETE).
 */

// Token CSRF leido del meta tag generado por base.html.
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

/**
 * Envoltorio de fetch() que agrega automaticamente el header
 * X-CSRFToken requerido por Flask-WTF en peticiones que modifican datos.
 */
function fetchProtegido(url, opciones = {}) {
    const cabeceras = Object.assign(
        { 'X-CSRFToken': CSRF_TOKEN },
        opciones.headers || {}
    );
    return fetch(url, Object.assign({}, opciones, { headers: cabeceras }));
}

function actualizarReloj() {
    const elemento = document.getElementById('relojActual');
    if (!elemento) return;

    const ahora = new Date();
    const opciones = { weekday: 'long', day: '2-digit', month: 'short' };
    const fecha = ahora.toLocaleDateString('es-ES', opciones);
    const hora = ahora.toLocaleTimeString('es-ES');

    elemento.innerHTML = `<i class="bi bi-clock"></i> ${fecha} &middot; ${hora}`;
}

document.addEventListener('DOMContentLoaded', () => {
    actualizarReloj();
    setInterval(actualizarReloj, 1000);
});
