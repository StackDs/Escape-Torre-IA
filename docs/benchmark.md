# Ejecución y reanudación del benchmark

El ejecutor está en `src/evaluation/benchmark.py`. Requiere Python, NumPy y un sistema con `fcntl` (Linux/macOS) para impedir dos ejecutores simultáneos sobre la misma carpeta. Las búsquedas no reciben límites de tiempo nuevos.

## Ejecutar desde la raíz del repositorio

```bash
python3 -m src.evaluation.benchmark --config configs/piloto_inicial.json --salida results/raw/piloto_inicial
```

Repetir exactamente ese comando reanuda la ejecución: las corridas finalizadas no vuelven a simularse. Una interrupción durante una corrida obliga a repetir solo esa corrida, no las ya guardadas.

Para dividir el trabajo en lotes de intentos nuevos:

```bash
python3 -m src.evaluation.benchmark --config configs/piloto_inicial.json --salida results/raw/piloto_inicial --limite-ejecuciones 5
```

`Ctrl+C` conserva los resultados completos. El comando devuelve código 130 al interrumpirse, 1 ante errores y 0 al terminar normalmente o alcanzar el límite de lote. Un lote que termina normalmente puede dejar ejecuciones pendientes: revisar `progreso.json`.

## Configuración JSON

### Ejecutar todas las búsquedas sin el genético

Desde la raíz, `python3 -u bench_sin_genetico.py` ejecuta BFS, DFS, UCS, A*, Greedy e IDA*. Usa los mapas, poblaciones, semillas y parámetros de `configs/benchmark_final.json`, sin requerir una política entrenada. Con la configuración actual son 10800 corridas (3 mapas × 3 poblaciones × 200 semillas × 6 algoritmos). Las poblaciones son 80, 180 y 300 agentes: cada cantidad se evalúa por separado en cada mapa.

El reporte se guarda en `results/raw/bench_sin_genetico_200/reporte_benchmark.txt`. Repetir el comando reanuda los resultados de esa carpeta si la configuración y el código no cambiaron. Esta carpeta separa la configuración de 200 iteraciones de ejecuciones anteriores.

Para una revisión preliminar con dos semillas por mapa, población y algoritmo (108 corridas):

```bash
python3 -u bench_sin_genetico.py --iteraciones 2 --salida results/raw/bench_sin_genetico_piloto
```

Una selección menor a 80 semillas se etiqueta como piloto. `--iteraciones` toma las primeras semillas del JSON; no altera las poblaciones ni el fuego. Usar una carpeta distinta al cambiar la configuración. También se admiten `--config` y `--limite-ejecuciones`. El programa ejecuta las búsquedas secuencialmente: una corrida lenta de IDA* puede demorar el avance.

### Campos

El archivo contiene `modo` (`piloto` o `final`), listas de `mapas`, `poblaciones`, `semillas` y `algoritmos`, y un diccionario `parametros` común. El ejecutor recorre su producto cartesiano; no cambia parámetros según el algoritmo. Las semillas se emparejan para todas las estrategias.

Las rutas de mapas y política entrenada se resuelven respecto a la raíz del proyecto. Las rutas de `--config` y `--salida` se resuelven respecto al directorio de ejecución. La configuración efectiva y las rutas resueltas quedan en el manifiesto.

Algoritmos admitidos: `bfs`, `dfs`, `ucs`, `a_star`, `ida_star`, `greedy` y `genetico`. El modo final exige al menos 80 semillas por configuración; el piloto no impone ese mínimo. El ejecutor no sustituye algoritmos ni omite corridas problemáticas silenciosamente.

Para `genetico`, incluir `politica_genetica` con la ruta al JSON producido por el entrenamiento. Debe registrar parámetros y semillas de entrenamiento. Se rechaza cualquier coincidencia entre semillas de entrenamiento y evaluación. El ejecutor usa una política ya entrenada; no realiza entrenamiento.

IDA* está disponible para una evaluación futura, pero no forma parte de los pilotos ejecutados aquí, por la indicación de omitir su comprobación de rendimiento.

## Archivos producidos

- `manifiesto.json`: configuración efectiva, huellas SHA-256 de mapas y código Python, versiones de Python/NumPy, commit de Git informativo y fecha de creación. Las huellas incluyen código no confirmado en Git.
- `corridas/<id>.json`: resultado completo por mapa, población, algoritmo y semilla. Se escribe mediante reemplazo atómico y sincronización del archivo.
- `resultados.csv`: una fila por corrida exitosa; se reconstruye desde los puntos de guardado al reanudar.
- `reporte_benchmark.txt`: tabla por población, mapa y algoritmo con supervivencia porcentual, media, desviación estándar, mínimo y máximo de turnos del último evacuado. Se actualiza después de cada corrida y al detenerse, indicando si el benchmark está completo o parcial.
- `progreso.json`: cantidad total, completada, pendiente y errores de la invocación más reciente.
- `errores/<id>.json`: diagnóstico del último fallo registrado para ese caso. Es histórico: puede existir aunque un intento posterior haya terminado correctamente; `corridas/` y `progreso.json` determinan qué falta.

No se guardan resultados parciales de una simulación como si fueran completos. Los errores del motor tampoco se convierten en cero supervivencia. Las ejecuciones interrumpidas por `max_turnos`, en cambio, son resultados válidos con personas pendientes.

Una carpeta no puede mezclar distintas configuraciones, código, mapas, política o versiones de Python/NumPy. Si algo cambia, seleccionar otra carpeta. Los archivos `.tmp` que pudiera dejar un cierre abrupto no se consideran puntos de guardado completos.

## Interpretación de métricas

`supervivencia` es una fracción de 0 a 1. `turno_ultimo_evacuado` aparece vacío en CSV cuando nadie evacúa; no representa cero turnos. `turnos_ejecutados` es la duración efectiva de la simulación y puede ser mayor que el turno del último evacuado. `pendientes` identifica personas vivas no evacuadas al límite.

El TXT promedia la supervivencia de todas las corridas completadas de cada grupo. Para Media, Std, Min y Max utiliza `turno_ultimo_evacuado`: excluye los casos sin evacuados y muestra `N/D` cuando no hay tiempos. Std es la desviación estándar muestral (n−1), por lo que requiere al menos dos tiempos. Las corridas que alcanzan el límite con algún evacuado conservan su tiempo observado; el reporte indica cuántas llegaron al límite y cuántas aportaron tiempos para interpretar estas estadísticas.

`segundos_ejecucion` se guarda solo como información operativa. No es la métrica principal solicitada ni se utiliza para elegir el algoritmo ganador. El tiempo total del TXT suma estos segundos entre todas las corridas completadas guardadas, incluidas las de invocaciones anteriores: no incluye pausas, intentos fallidos, corridas interrumpidas ni exportaciones. Los gráficos quedan pendientes.

## Generar el TXT de un benchmark existente

No es necesario repetir las simulaciones:

```bash
python3 -m src.evaluation.benchmark --solo-reporte --salida results/raw/piloto_inicial
```

Este comando lee el manifiesto y las corridas guardadas, valida los resultados y escribe `reporte_benchmark.txt`. Permite exportar datos de versiones anteriores sin disponer de los mapas o la política original; no modifica los resultados ni autoriza reanudar simulaciones con una versión distinta. La carpeta no debe tener una ejecución activa. Los nuevos benchmarks generan el TXT automáticamente con el comando habitual.

## Separación de datos

Las semillas 100 y 101 se usan para calibración piloto. Reservar semillas distintas para entrenamiento (por ejemplo, 1000–1099) y para el benchmark final (10000–10199, las 200 semillas de la configuración preparada). No reutilizar las semillas piloto como evaluación final después de elegir parámetros con ellas.

El protocolo seleccionado y los resultados de calibración se documentan en `calibracion_piloto.md`. Un piloto de dos semillas por configuración es una comprobación preliminar, no evidencia de superioridad estadística de una estrategia.
