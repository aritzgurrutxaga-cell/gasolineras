// diario.js
async function renderizarGasolineras() {
    const contenedor = document.getElementById('resultados');
    
    try {
        // Accedemos al archivo que ya está en tu repo
        const response = await fetch('./precios_gasolineras.json');
        const data = await response.json();
        
        // Aquí llamas a la lógica de filtrado que definimos antes
        const provincias = ["GIPUZKOA", "ÁLAVA", "NAVARRA", "BIZKAIA"];
        const filtrados = obtener_gasolineras_mas_baratas(data, provincias);

        // Renderizado básico
        contenedor.innerHTML = Object.entries(filtrados).map(([provincia, tipos]) => `
            <section class="card-provincia">
                <h2>${provincia}</h2>
                <div class="grid-precios">
                    ${renderizarTipo(tipos["Gasolina 95 E5"], "Gasolina 95 E5")}
                    ${renderizarTipo(tipos["Gasoleo A"], "Gasóleo A")}
                </div>
            </section>
        `).join('');
        
    } catch (error) {
        console.error("Error al cargar el JSON:", error);
        contenedor.innerHTML = "<p>Hubo un error al cargar los precios.</p>";
    }
}

function renderizarTipo(lista, titulo) {
    return `
        <div class="columna-tipo">
            <h4>${titulo}</h4>
            <ul>
                ${lista.map(g => `<li>${g.Rotulo}: ${g.Precio}€ (${g.Localidad})</li>`).join('')}
            </ul>
        </div>
    `;
}

renderizarGasolineras();
