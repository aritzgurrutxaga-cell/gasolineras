async function cargarPrecios() {
    const contenedor = document.getElementById('contenedor-gasolineras');
    
    try {
        const response = await fetch(`./precios_gasolineras.json?t=${Date.now()}`);
        const data = await response.json();
        const provinciasInteres = ["GIPUZKOA", "ÁLAVA", "NAVARRA", "BIZKAIA"];
        
        // Estructura: resultados[provincia][tipoCombustible] = {datos_gasolinera}
        const resultados = {};

        data.datos.forEach(estacion => {
            const prov = estacion.Provincia ? estacion.Provincia.toUpperCase() : "";
            const target = provinciasInteres.find(p => prov.includes(p) || (p === "ÁLAVA" && prov.includes("ARABA")));

            if (target) {
                if (!resultados[target]) resultados[target] = {};

                // Buscamos todas las claves que empiezan por "Precio"
                Object.keys(estacion).forEach(key => {
                    if (key.startsWith("Precio") && estacion[key] !== "") {
                        const precioActual = parseFloat(estacion[key].replace(',', '.'));
                        
                        // Si no existe este tipo de combustible o el nuevo es más barato, guardamos
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

        // Renderizado
        let html = "";
        for (const prov of provinciasInteres) {
            html += `<section class="card-provincia"><h1>${prov}</h1>`;
            const combustibles = resultados[prov] || {};
            
            Object.values(combustibles).forEach(g => {
                html += `<div class="estacion-card" style="border:1px solid #007bff; margin:10px 0; padding:15px; border-radius:8px;">
                            <h3 style="margin-top:0;">${g.nombreCombustible}: ${g.precioNum.toFixed(3)}€</h3>
                            <p><strong>Rótulo:</strong> ${g.Rótulo}<br>
                            <strong>Localidad:</strong> ${g.Localidad}<br>
                            <strong>Dirección:</strong> ${g.Dirección}</p>
                        </div>`;
            });
            html += `</section>`;
        }
        
        contenedor.innerHTML = html;

    } catch (error) {
        contenedor.innerHTML = `<p style="color:red;">Error al procesar: ${error.message}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', cargarPrecios);
