/**
 * static/js/eliminar.js
 * Pide confirmacion con SweetAlert2 antes de eliminar un estudiante y,
 * si se confirma, envia un POST protegido con CSRF a /borrar/<uid>.
 * Reemplaza el enlace GET del codigo original (un solo click borraba
 * sin confirmar) por un flujo explicito de dos pasos.
 */

document.addEventListener('DOMContentLoaded', () => {
    const lista = document.getElementById('listaEstudiantes');
    if (!lista) return;

    lista.addEventListener('click', async (evento) => {
        const boton = evento.target.closest('.btn-eliminar');
        if (!boton) return;

        const uid = boton.dataset.uid;
        const nombre = boton.dataset.nombre;

        const confirmacion = await Swal.fire({
            icon: 'warning',
            title: '¿Eliminar estudiante?',
            html: `Se eliminara a <strong>${nombre}</strong> (<span class="mono">${uid}</span>) del sistema.`,
            showCancelButton: true,
            confirmButtonText: 'Si, eliminar',
            cancelButtonText: 'Cancelar',
            confirmButtonColor: '#DC2626',
            cancelButtonColor: '#64748B',
        });

        if (!confirmacion.isConfirmed) return;

        boton.disabled = true;

        try {
            const respuesta = await fetchProtegido(`/borrar/${encodeURIComponent(uid)}`, {
                method: 'POST',
            });
            const resultado = await respuesta.json();

            if (resultado.status === 'success') {
                const fila = lista.querySelector(`.estudiante-row[data-uid="${uid}"]`);
                if (fila) fila.remove();

                Swal.fire({
                    icon: 'success',
                    title: 'Estudiante eliminado',
                    text: resultado.message,
                    timer: 1800,
                    showConfirmButton: false,
                });
            } else {
                boton.disabled = false;
                Swal.fire({
                    icon: 'error',
                    title: 'No se pudo eliminar',
                    text: resultado.message || 'Intenta de nuevo.',
                    confirmButtonColor: '#2F6FED',
                });
            }
        } catch (error) {
            boton.disabled = false;
            Swal.fire({
                icon: 'error',
                title: 'Error de conexion',
                text: 'No se pudo contactar al servidor. Intenta de nuevo.',
                confirmButtonColor: '#2F6FED',
            });
        }
    });
});
