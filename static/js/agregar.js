/**
 * static/js/agregar.js
 * Envia el formulario de alta de estudiantes via AJAX (sin recargar la
 * pagina) y muestra el resultado con SweetAlert2. La validacion real
 * (UID, nombre, chat_id) ocurre en el servidor (forms.py); aqui solo
 * se interpreta la respuesta JSON.
 */

document.addEventListener('DOMContentLoaded', () => {
    const formulario = document.getElementById('formAgregar');
    if (!formulario) return;

    formulario.addEventListener('submit', async (evento) => {
        evento.preventDefault();

        const boton = formulario.querySelector('button[type="submit"]');
        const textoOriginal = boton.innerHTML;
        boton.disabled = true;
        boton.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Guardando...';

        try {
            const respuesta = await fetchProtegido(formulario.action || window.location.pathname, {
                method: 'POST',
                body: new FormData(formulario),
            });

            const resultado = await respuesta.json();

            if (resultado.status === 'success') {
                await Swal.fire({
                    icon: 'success',
                    title: 'Estudiante guardado',
                    text: resultado.message,
                    confirmButtonColor: '#2F6FED',
                });
                formulario.reset();
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'No se pudo guardar',
                    text: resultado.message || 'Revisa los datos ingresados.',
                    confirmButtonColor: '#2F6FED',
                });
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Error de conexion',
                text: 'No se pudo contactar al servidor. Intenta de nuevo.',
                confirmButtonColor: '#2F6FED',
            });
        } finally {
            boton.disabled = false;
            boton.innerHTML = textoOriginal;
        }
    });
});
