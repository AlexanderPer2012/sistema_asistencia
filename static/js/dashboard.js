/**
 * static/js/dashboard.js
 * Carga via AJAX las tarjetas de resumen, los 4 graficos (Chart.js) y
 * la tabla de asistencias (DataTables) del panel.
 *
 * Las tarjetas y los graficos usan rangos fijos definidos en el
 * servidor (hoy / ultimos 7 dias / ultimas 8 semanas / ultimos 6
 * meses); solo la tabla cambia segun el filtro dia/semana/mes
 * seleccionado con los botones de arriba.
 */

(() => {
    const raiz = document.getElementById('dashboardRoot');
    if (!raiz) return;

    let filtroActual = raiz.dataset.filtroActual || 'dia';
    let tabla = null;
    const graficos = {};

    const COLOR_VERDE = '#16A34A';
    const COLOR_NARANJA = '#D97706';
    const COLOR_AZUL = '#2F6FED';

    /** 'YYYY-MM-DD HH:MM:SS' -> 'DD/MM/YYYY HH:MM:SS' (legible para personas). */
    function formatearFechaHora(texto) {
        if (!texto) return '';
        const [fecha, hora] = texto.split(' ');
        const [anio, mes, dia] = fecha.split('-');
        return `${dia}/${mes}/${anio} ${hora || ''}`.trim();
    }

    async function cargarResumen() {
        const respuesta = await fetch('/dashboard/api/resumen');
        const datos = await respuesta.json();

        document.getElementById('statTotalEstudiantes').textContent = datos.total_estudiantes;
        document.getElementById('statEntradasHoy').textContent = datos.entradas_hoy;
        document.getElementById('statSalidasHoy').textContent = datos.salidas_hoy;

        document.getElementById('statUltimoEstudiante').textContent =
            datos.ultimo_estudiante ? datos.ultimo_estudiante.nombre : 'Sin registros';

        const elUltimoAcceso = document.getElementById('statUltimoAcceso');
        if (datos.ultimo_acceso) {
            const evento = datos.ultimo_acceso.evento;
            const claseBadge = evento === 'ENTRADA' ? 'badge-entrada' : 'badge-salida';
            elUltimoAcceso.innerHTML = `
                <span class="badge ${claseBadge}">${evento}</span>
                &nbsp;<strong>${datos.ultimo_acceso.nombre}</strong>
                <span class="mono" style="color: var(--gris-texto);">(${datos.ultimo_acceso.uid})</span>
                &middot; ${formatearFechaHora(datos.ultimo_acceso.fecha_hora)}
            `;
        } else {
            elUltimoAcceso.textContent = 'Aun no se han registrado marcajes.';
        }
    }

    function crearOActualizarGrafico(idCanvas, tipo, etiquetas, valores, color, etiquetaSerie) {
        const lienzo = document.getElementById(idCanvas);
        if (!lienzo) return;

        if (graficos[idCanvas]) {
            graficos[idCanvas].data.labels = etiquetas;
            graficos[idCanvas].data.datasets[0].data = valores;
            graficos[idCanvas].update();
            return;
        }

        graficos[idCanvas] = new Chart(lienzo, {
            type: tipo,
            data: {
                labels: etiquetas,
                datasets: [{
                    label: etiquetaSerie,
                    data: valores,
                    backgroundColor: tipo === 'bar' ? `${color}33` : `${color}22`,
                    borderColor: color,
                    borderWidth: 2,
                    borderRadius: tipo === 'bar' ? 6 : 0,
                    tension: 0.35,
                    fill: tipo === 'line',
                    pointRadius: tipo === 'line' ? 3 : 0,
                    pointBackgroundColor: color,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    async function cargarGraficos() {
        const respuesta = await fetch('/dashboard/api/graficos');
        const datos = await respuesta.json();

        crearOActualizarGrafico(
            'graficoEntradas', 'bar',
            datos.entradas_diarias.map((p) => p.fecha.slice(5)),
            datos.entradas_diarias.map((p) => p.total),
            COLOR_VERDE, 'Entradas'
        );
        crearOActualizarGrafico(
            'graficoSalidas', 'bar',
            datos.salidas_diarias.map((p) => p.fecha.slice(5)),
            datos.salidas_diarias.map((p) => p.total),
            COLOR_NARANJA, 'Salidas'
        );
        crearOActualizarGrafico(
            'graficoSemanal', 'line',
            datos.semanal.map((p) => p.semana),
            datos.semanal.map((p) => p.total),
            COLOR_AZUL, 'Asistencias'
        );
        crearOActualizarGrafico(
            'graficoMensual', 'line',
            datos.mensual.map((p) => p.mes),
            datos.mensual.map((p) => p.total),
            COLOR_AZUL, 'Asistencias'
        );
    }

    async function cargarTabla(filtro) {
        const respuesta = await fetch(`/dashboard/api/asistencias?filtro=${encodeURIComponent(filtro)}`);
        const datos = await respuesta.json();

        const etiqueta = document.getElementById('etiquetaRango');
        if (etiqueta) etiqueta.innerHTML = `<i class="bi bi-calendar3"></i> ${datos.rango}`;

        if (tabla) {
            tabla.clear();
            tabla.rows.add(datos.data);
            tabla.draw();
            return;
        }

        tabla = $('#tablaAsistencias').DataTable({
            data: datos.data,
            columns: [
                { data: 'uid', className: 'mono' },
                { data: 'nombre' },
                {
                    data: 'evento',
                    render: (valor) => {
                        const clase = valor === 'ENTRADA' ? 'badge-entrada' : 'badge-salida';
                        return `<span class="badge ${clase}">${valor}</span>`;
                    },
                },
                {
                    data: 'fecha_hora',
                    className: 'mono',
                    render: (valor) => formatearFechaHora(valor),
                },
            ],
            order: [],
            dom: 'Bfrtip',
            buttons: [
                { extend: 'excelHtml5', text: '<i class="bi bi-file-earmark-excel"></i> Excel', className: 'btn btn-outline-oscuro btn-sm' },
                { extend: 'pdfHtml5', text: '<i class="bi bi-file-earmark-pdf"></i> PDF', className: 'btn btn-outline-oscuro btn-sm' },
                { extend: 'csvHtml5', text: '<i class="bi bi-file-earmark-text"></i> CSV', className: 'btn btn-outline-oscuro btn-sm' },
            ],
            language: {
                search: 'Buscar:',
                lengthMenu: 'Mostrar _MENU_ registros',
                info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
                infoEmpty: 'Sin registros disponibles',
                infoFiltered: '(filtrado de _MAX_ registros totales)',
                paginate: { previous: 'Anterior', next: 'Siguiente' },
                zeroRecords: 'No se encontraron coincidencias',
            },
        });
    }

    function activarBoton(filtro) {
        document.querySelectorAll('.filtro-rango .btn').forEach((boton) => {
            const esActivo = boton.dataset.filtro === filtro;
            boton.classList.toggle('btn-electrico', esActivo);
            boton.classList.toggle('btn-outline-oscuro', !esActivo);
        });
    }

    cargarResumen();
    cargarGraficos();
    cargarTabla(filtroActual);

    document.querySelectorAll('.filtro-rango .btn').forEach((boton) => {
        boton.addEventListener('click', () => {
            filtroActual = boton.dataset.filtro;
            activarBoton(filtroActual);
            cargarTabla(filtroActual);
        });
    });
})();
