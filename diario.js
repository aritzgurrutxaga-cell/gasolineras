async function cargarPrecios() {
    const contenedor = document.getElementById('contenedor-gasolineras');
    
    try {
        // Obtenemos el archivo
        const response = await fetch(`./precios_gasolineras.json?t=${Date.now()}`);
        const data = await response.json();
        
        // Provincias de interés
        const provinciasInteres = ["GIPUZKOA", "ÁLAVA", "NAVARRA", "BIZKAIA"];
        
        // Estructura para agrupar
        const agrupado = {};
        provinciasInteres.forEach(p => agrupado[p] = []);

        // Procesar todos los datos
        data.datos.forEach(estacion => {
            const prov = estacion.Provincia ? estacion.Provincia.toUpperCase() : "";
            const target = provinciasInteres.find(p => prov.includes(p) || (p === "ÁLAVA" && prov.includes("ARABA")));

            if (target) {
                agrupado[target].push(estacion);
            }
        });

        // Generar el HTML dinámico
        let html = "";
        for (const prov of provinciasInteres) {
            html += `<section class="card-provincia"><h1>${prov}</h1>`;
            
            agrupado[prov].forEach(estacion => {
                html += `<div class="estacion-card" style="border:1px solid #ccc; margin:10px 0; padding:10px;">
                            <h3>${estacion.Rótulo || "Sin nombre"}</h3>
                            <div class="datos-grid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 5px;">`;
                
                // AQUÍ ESTÁ EL CAMBIO: Recorremos todas las claves existentes
                Object.entries(estacion).forEach(([key, value]) => {
                    if (value && value !== "") { // Solo mostrar si tiene valor
                        html += `<div><strong>${key}:</strong> ${value}</div>`;
                    }
                });
                
                html += `</div></div>`;
            });
            html += `</section>`;
        }
        
        contenedor.innerHTML = html;

    } catch (error) {
        contenedor.innerHTML = `<p style="color:red;">Error al cargar: ${error.message}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', cargarPrecios);
