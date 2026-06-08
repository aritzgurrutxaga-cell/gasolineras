async function cargarPrecios() {
    const contenedor = document.getElementById('contenedor-gasolineras');
    
    try {
        // El timestamp ?t=${Date.now()} evita que el navegador muestre datos viejos
        const response = await fetch(`./precios_gasolineras.json?t=${Date.now()}`);
        const data = await response.json();
        
        const provinciasInteres = ["GIPUZKOA", "ÁLAVA", "NAVARRA", "BIZKAIA"];
        const resultados = {};

        // Inicializar estructura
        provinciasInteres.forEach(p => resultados[p] = { "Gasolina 95 E5": [], "Gasoleo A": [] });

        data.datos.forEach(estacion => {
            const prov = estacion.Provincia.toUpperCase();
            let target = null;
            
            // Mapeo flexible por si hay variaciones en el nombre de la provincia
            if (prov.includes("GIPUZKOA")) target = "GIPUZKOA";
            else if (prov.includes("ÁLAVA") || prov.includes("ARABA")) target = "ÁLAVA";
            else if (prov.includes("NAVARRA")) target = "NAVARRA";
            else if (prov.includes("BIZKAIA")) target = "BIZKAIA";

            if (target) {
                // Función interna para limpiar y convertir precio
                const precio = (campo) => estacion[campo] ? parseFloat(estacion[campo].replace(',', '.')) : null;

                const pGas95 = precio("Precio Gasolina 95 E5");
                const pDiesel = precio("Precio Gasoleo A");

                if (pGas95) resultados[target]["Gasolina 95 E5"].push({ ...estacion, precioNum: pGas95 });
                if (pDiesel) resultados[target]["Gasoleo A"].push({ ...estacion, precioNum: pDiesel });
            }
        });

        // Ordenar y limitar a las 3 más baratas por categoría
        let html = "";
        for (const prov of provinciasInteres) {
            html += `<section class="card-provincia"><h2>${prov}</h2><div class="grid-precios">`;
            
            ["Gasolina 95 E5", "Gasoleo A"].forEach(tipo => {
                const top3 = resultados[prov][tipo].sort((a, b) => a.precioNum - b.precioNum).slice(0, 3);
                html += `<div class="columna-tipo"><h4>${tipo}</h4><ul>`;
                top3.forEach(g => {
                    html += `<li><strong>${g.Rótulo}</strong><br>${g.Localidad} - ${g.precioNum.toFixed(3)}€</li>`;
                });
                html += `</ul></div>`;
            });
            
            html += `</div></section>`;
        }
        
        contenedor.innerHTML = html;

    } catch (error) {
        contenedor.innerHTML = "<p>Error al cargar los datos. Revisa que el archivo JSON esté en la ruta correcta.</p>";
        console.error(error);
    }
}

document.addEventListener('DOMContentLoaded', cargarPrecios);
