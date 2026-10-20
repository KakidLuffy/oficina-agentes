# Oficina de agentes en la nube (gratis, sin tu PC)

Esto ejecuta tus 4 agentes **cada hora** en los servidores de GitHub, con precios reales de BTC/EUR y dinero **ficticio**. Los resultados se guardan solos en tu repositorio y los puedes ver desde el móvil o el ordenador.

No hace falta instalar nada ni usar la terminal. Todo se hace desde la web.

## Archivos que necesitas

- `agentes_nube.py`: el programa (un paso por ejecución).
- `agentes.yml`: la orden que le dice a GitHub que lo ejecute cada hora.

## Paso a paso

**1. Crea una cuenta en github.com** (gratis). Si ya tienes, salta este paso.

**2. Crea un repositorio.**
- Arriba a la derecha pulsa **+ → New repository**.
- Nombre: `oficina-agentes`.
- Marca **Private** (privado) para que solo tú veas los resultados.
- Marca **Add a README file** y pulsa **Create repository**.

**3. Sube el programa.**
- En el repositorio pulsa **Add file → Upload files**.
- Arrastra `agentes_nube.py` y pulsa **Commit changes**.

**4. Crea la orden de ejecución.**
- Pulsa **Add file → Create new file**.
- En el nombre escribe exactamente: `.github/workflows/agentes.yml` (al escribir las barras `/` se crean las carpetas solas).
- Abre `agentes.yml` con el Bloc de notas, copia todo su contenido y pégalo en el cuadro grande.
- Pulsa **Commit changes**.

**5. Pruébalo una vez a mano.**
- Ve a la pestaña **Actions**.
- Si te pide activar los workflows, acepta.
- Elige **Agentes de trading (simulación)** en la lista de la izquierda y pulsa **Run workflow → Run workflow**.
- Espera 1 minuto y recarga. Debe salir un círculo verde.

**6. Mira los resultados.**
- Vuelve a la pestaña **Code**: ha aparecido una carpeta `datos`.
- Abre `datos/resumen.md`: tiene la tabla de los agentes y la comparación con comprar y mantener.
- `datos/historial.csv` guarda la evolución hora a hora y `datos/operaciones.csv` cada compra y venta.

A partir de ahí se ejecuta solo cada hora. Los agentes solo operan cuando se cierra una vela de 1 hora, así que pueden pasar horas sin ninguna operación.

## Qué esperar

- **Dale semanas.** Con pocos días de datos no se puede distinguir una buena estrategia de la suerte.
- **El criterio para seguir:** que un agente supere a "Comprar y mantener" de forma sostenida durante varias semanas, después de comisiones. Si ninguno lo hace, la conclusión válida es que esas estrategias no sirven, y no habrás perdido dinero real.
- **Las ejecuciones de GitHub pueden retrasarse** unos minutos (o más en horas de mucha carga) y alguna puede saltarse. El programa lo tiene en cuenta: si se retrasa, procesa las velas pendientes en orden.

## Cosas que conviene saber

- **Gratis con condiciones.** En repositorios públicos GitHub no cobra las ejecuciones. En privados hay una cuota mensual gratuita según tu plan, y esta simulación usa muy poco (una ejecución de menos de un minuto por hora). Comprueba tu cuota en *Settings → Billing* de tu cuenta de GitHub, porque las condiciones pueden cambiar.
- **Tareas programadas desactivadas.** Según recuerdo, GitHub puede desactivar las tareas programadas de un repositorio tras un periodo largo sin actividad. Si las ejecuciones dejan de aparecer, entra en **Actions** y reactiva el workflow con un clic. Confírmalo en la documentación de GitHub.
- **Para pararlo:** **Actions → Agentes de trading (simulación) → ⋯ → Disable workflow**.
- **Seguridad:** este programa no usa claves ni contraseñas, y no debe tenerlas nunca. No subas claves de ningún exchange al repositorio.
- **Es una simulación.** No opera en ningún exchange ni toca dinero real.

## Probarlo en tu PC (opcional)

Con Python instalado, en una carpeta con `agentes_nube.py`:

```
python agentes_nube.py
```

Hace un paso con precios reales y crea la carpeta `datos`. Para una prueba sin internet: `python agentes_nube.py --demo 120`.
