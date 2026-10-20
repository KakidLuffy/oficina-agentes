# Oficina de agentes en la nube (gratis, sin tu PC)

Seis agentes de trading con **dinero ficticio** (10 € cada uno, 60 € en total) que se ejecutan **cada hora en los servidores de GitHub**, con precios reales de Kraken. Pueden operar las **20 monedas de mayor volumen contra el euro** (BTC, ETH, SOL, XRP…), hasta 5 a la vez por agente. Los resultados se guardan solos en este repositorio y se ven en un panel web. El ordenador puede estar apagado.

**Es una simulación:** no opera en ningún exchange ni toca dinero real, y nada de esto garantiza beneficios.

## Qué hay en el repositorio

| Archivo | Para qué sirve |
|---|---|
| `agentes_nube.py` | El programa: un paso por ejecución (descarga precios, decide, anota). |
| `informe.py` | Calcula la caída máxima, las operaciones ganadoras/perdedoras y el gráfico del resumen. |
| `.github/workflows/agentes.yml` | La orden que ejecuta el programa cada hora (minutos 17 y 47, como respaldo). |
| `comparar_estrategias.py` y `.github/workflows/comparar.yml` | Comparador manual de estrategias sobre el historial de BTC/EUR (se lanza a mano desde Actions). |
| `laboratorio.py` y `.github/workflows/laboratorio.yml` | El laboratorio: cada lunes prueba ~80 variantes de estrategias y las examina (ver más abajo). |
| `index.html` | El panel «Sala de trading», publicado con GitHub Pages. |
| `manifest.webmanifest`, `icon-192.png`, `icon-512.png` | Permiten instalar el panel en la pantalla de inicio del móvil. |
| `director.py` y `.github/workflows/director.yml` | El director: tras cada ejecución de los agentes o del laboratorio revisa los datos y escribe el parte, la memoria y las propuestas. |
| `EQUIPO.md` | Carta del equipo: quién hace qué, qué necesita tu aprobación y qué está prohibido. |
| `datos/` | Resultados: `resumen.md`, `estado.json`, `historial_v2.csv`, `operaciones.csv`, `grafico.svg`, `laboratorio.json`, `laboratorio.md`, `parte_director.json` y `.md`, `memoria.jsonl` y `.md`, `propuestas.md` y `director_estado.json`. El `historial.csv` antiguo (4 agentes) se conserva sin tocar. |
| `comparacion/` | Resultado del comparador (`comparacion.md` y `.csv`). |

## Los agentes

| Agente | Qué hace |
|---|---|
| Cruce 10/30 y Cruce 5/20 | Compran cuando la media corta cruza por encima de la larga y venden al revés. |
| Momentum | Compra si el precio sube más de un 1,2 % en 12 horas y vende si baja otro tanto. |
| Rebote | Compra cuando el precio cae un 1,5 % bajo su media de 20 horas y vende al recuperarla. |
| Cruce 10/30 + filtro | Como el Cruce 10/30, pero solo compra si el precio está por encima de su media de 200 horas (tendencia alcista). |
| Consenso 2 de 3 | Compra cuando al menos 2 de las 3 reglas de tendencia (Cruce 10/30, Cruce 5/20, Momentum) coinciden. |

Los agentes deciden solo cuando se cierra una vela de 1 hora, así que pueden pasar horas sin ninguna operación.

## El laboratorio (analistas de estrategias)

Un grupo de tres analistas (tendencia, filtros y rebote) prueba cada lunes unas 80 variantes de estrategias sobre el historial de Kraken (6 monedas, velas de 4 horas y de 1 día). Funciona así:

1. **Entrenamiento:** se eligen las 12 mejores variantes con el primer 60 % del historial.
2. **Examen:** se las prueba en el último 40 %, que no se usó para elegir. Una variante aprueba si gana dinero y supera a comprar y mantener en al menos el 60 % de las series, con 4 operaciones o más.
3. **Tasa de azar:** se calcula qué porcentaje de *todas* las variantes aprobaría el examen. Si las candidatas no destacan claramente sobre ese porcentaje, el veredicto es «ruido».
4. **Director:** el veredicto (POSIBLE, RUIDO o NINGUNA) aparece en el panel, en la vista **Laboratorio**, y en el informe diario.

Modo «propone, no ejecuta»: las candidatas **no operan solas**. Si alguna se repite varias semanas, se puede añadir como agente nuevo en simulación y aplicarle el mismo criterio de 3 semanas y 30 operaciones. Se lanza a mano desde **Actions → Laboratorio de estrategias (semanal) → Run workflow**.

## El director

Después de cada ejecución de los agentes (y del laboratorio), el director, que **solo lee y resume**, hace cuatro cosas:

1. **Revisa los datos:** comprueba que están al día, que las cuentas cuadran, que no hay precios raros y que se respetan los límites. Si algo falla, el parte lo dice antes de que te fíes de las cifras.
2. **Escribe el parte del día** (`datos/parte_director.md`): capital, mejor y peor agente, avisos de riesgo y cuánto le falta a cada agente para ser evaluable (21 días y 30 cierres). Se ve en el panel, debajo de «De un vistazo».
3. **Anota en la memoria compartida** (`datos/memoria.md`) las reglas y el registro de decisiones: agentes que se apagan, agentes que ya son evaluables, veredictos del laboratorio.
4. **Prepara las propuestas** (`datos/propuestas.md`): las candidatas del laboratorio con cuántas semanas seguidas aparecen. Para aprobar o rechazar una, díselo a Claude o crea `datos/aprobaciones.txt` con líneas como `aprobar: Cruce 15/20`.

Para activarlo hay que subir `director.py` y crear `.github/workflows/director.yml`. Se puede lanzar a mano desde **Actions → Director de la oficina → Run workflow**.

## Ver los resultados

- **Panel web:** `https://kakidluffy.github.io/oficina-agentes/`. Aldea pixel-art con los agentes (con aviso «LISTO» cuando cierran una operación ganadora y su última operación), laboratorio, parte del director, ranking, mercado en vivo con gráficas de velas, operaciones, informe y control. Se puede guardar en marcadores o instalar en el móvil («Añadir a pantalla de inicio»).
- **Resumen en texto:** abre `datos/resumen.md` en el repositorio.
- **Informe diario:** una tarea programada lee estos datos cada mañana y te manda un resumen corto.

## Montarlo desde cero (paso a paso)

No hace falta instalar nada ni usar la terminal.

1. **Crea una cuenta en github.com** (gratis) y un repositorio llamado `oficina-agentes`.
2. **Sube los archivos:** **Add file → Upload files** con `agentes_nube.py`, `informe.py`, `comparar_estrategias.py`, `laboratorio.py` e `index.html`.
3. **Crea las órdenes de ejecución:** **Add file → Create new file**, con el nombre `.github/workflows/agentes.yml`, y pega el contenido de `agentes.yml`. Repite con `.github/workflows/comparar.yml` y `.github/workflows/laboratorio.yml`.
4. **Pruébalo a mano:** pestaña **Actions → Agentes de trading (simulación) → Run workflow**. Tras un minuto debe salir un círculo verde y aparecer la carpeta `datos`.
5. **Activa el panel (opcional):** **Settings → Pages → Source: Deploy from a branch → main / (root) → Save**. En uno o dos minutos estará en `https://TU-USUARIO.github.io/oficina-agentes/`.

A partir de ahí corre solo. Si cambias `agentes_nube.py`, se ejecuta de nuevo automáticamente.

## Costes y límites simulados

- Cada operación paga una **comisión del 0,25 %** y un **deslizamiento** del 0,05 % (0,3 % en monedas de poco volumen): comprar sale un poco más caro y vender un poco más barato. Los valores están al principio de `agentes_nube.py` (`FEE`, `SLIP`, `SLIP_POCO_VOLUMEN`).
- **Reparto:** cada agente invierte 2 € por moneda y puede tener hasta 5 a la vez.
- **Límite de pérdida diaria:** si un agente pierde 0,40 € (un 4 %) en un día, no vuelve a comprar ese día. Si baja de 7 € (un 30 % de pérdida), se apaga.
- **Más monedas:** el número de monedas vigiladas se cambia con `TOP_MONEDAS`. Subirlo alarga la ejecución y aumenta la probabilidad de que alguna estrategia parezca buena solo por azar.

## Qué esperar (y cuándo fiarse)

- **Un agente solo es evaluable con al menos 30 operaciones cerradas y 3 semanas de simulación.** Hasta entonces el resumen y el panel muestran un aviso ⚠: el resultado puede ser pura suerte.
- **El criterio para seguir:** que un agente supere a «Comprar y mantener» de forma sostenida, después de costes. Cada agente se compara con comprar BTC el día en que él empezó. Si ninguno lo consigue, la conclusión válida es que esas estrategias no sirven, y no habrás perdido dinero real.
- **Cuantas más estrategias y monedas pruebas, más fácil es que alguna salga bien por casualidad.** Tómalo como candidato, no como prueba.
- Las ejecuciones de GitHub pueden retrasarse o saltarse alguna vez; el programa procesa las velas pendientes en orden.

## Cosas que conviene saber

- **Repositorio público:** el informe diario y el panel lo leen sin claves. Por eso **nunca subas claves ni contraseñas de ningún exchange**; este programa no las usa ni las necesita.
- **Gratis con condiciones.** En repositorios públicos GitHub no cobra las ejecuciones. Comprueba las condiciones actuales en la documentación de GitHub.
- **Tareas programadas desactivadas.** GitHub puede desactivarlas tras un periodo largo sin actividad en el repositorio. Si las ejecuciones dejan de aparecer, entra en **Actions** y reactiva el flujo con un clic.
- **Para pararlo:** **Actions → Agentes de trading (simulación) → ⋯ → Disable workflow**.
- **Reiniciar desde cero:** borra la carpeta `datos` y deja que se ejecute de nuevo. Los agentes empiezan otra vez con 10 € (si cambias el capital en el código, la simulación anterior se archiva sola en `datos/archivo_…`).

## Probarlo en tu PC (opcional)

Con Python instalado, en una carpeta con `agentes_nube.py` e `informe.py`:

```
python agentes_nube.py
```

Hace un paso con precios reales y crea la carpeta `datos`. Para una prueba sin internet: `python agentes_nube.py --demo 120`.
