async function cargarPrecios() {
    const contenedor = document.getElementById('contenedor-gasolineras');
    
    try {
        const response = await fetch(`./precios_gasolineras.json?t=${Date.now()}`);
        const data = await response.json();
        const provinciasInteres = ["GIPUZKOA", "ÁLAVA", "NAVARRA", "BIZKAIA"];
        const resultados = {};

        data.datos.forEach(estacion => {
            const prov = estacion.Provincia ? estacion.Provincia.toUpperCase() : "";
            const target = provinciasInteres.find(p => prov.includes(p) || (p === "ÁLAVA" && prov.includes("ARABA")));

            if (target) {
                if (!resultados[target]) resultados[target] = {};

                Object.keys(estacion).forEach(key => {
                    // Filtramos solo columnas que empiezan por "Precio" para comparar
                    if (key.startsWith("Precio") && estacion[key] !== "") {
                        const precioActual = parseFloat(estacion[key].replace(',', '.'));
                        
                        if (!resultados[target][key] || precioActual < resultados[target][key].precioNum) {
                            resultados[target][key] = {
                                ...estacion,
                                precioNum: precioActual,
                                nombreCombustible: key
                            };
                        }
                    }
                });
            }
        });

        let html = "";
        provinciasInteres.forEach(prov => {
            html += `<section class="card-provincia"><h1>${prov}</h1>`;
            const combustibles = resultados[prov] || {};
            
            Object.values(combustibles).forEach(g => {
                html += `<div class="estacion-card" style="border:1px solid #333; margin:15px 0; padding:15px; border-radius:8px; background:#fff;">
                            <h2 style="color:#007bff;">${g.nombreCombustible}: ${g.precioNum.toFixed(3)}€</h2>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9em;">`;
                
                // AQUÍ: Recorremos TODAS las columnas del JSON para este objeto
                Object.entries(g).forEach(([key, value]) => {
                    if (key !== "precioNum" && value !== "") {
                        html += `<div><strong>${key}:</strong> ${value}</div>`;
                    }
                });
                
                html += `</div></div>`;
            });
            html += `</section>`;
        });
        
        contenedor.innerHTML = html;

    } catch (error) {
        contenedor.innerHTML = `<p style="color:red;">Error al procesar: ${error.message}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', cargarPrecios);
