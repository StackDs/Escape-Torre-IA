# Calibración piloto del benchmark

Fecha: 26 de septiembre de 2026.

## Alcance realizado

Se ejecutaron dos perfiles con 36 corridas cada uno: tres mapas, poblaciones de 80, 180 y 300 agentes, semillas 100 y 101, y BFS/A*. Total: **72 simulaciones completas**, sin errores y sin personas pendientes al límite. No hubo ejecuciones sin evacuados.

Se omitió la comprobación de rendimiento de IDA* por indicación del usuario. Tampoco se entrenó el genético ni se ejecutó el benchmark final. El piloto no determina qué algoritmo es mejor.

## Perfiles comparados

Ambos usaron capacidad 4 por pasillo, capacidad 2 en la salida, dos focos, probabilidad 0.4 por candidata, máximo de 1000 turnos, alpha 1.0 y umbral de bloqueo 3. Se cambió solamente la frecuencia:

- `configs/piloto_inicial.json`: fuego cada 3 turnos.
- `configs/piloto_fuego_frecuente.json`: fuego cada turno.

Se reutilizaron las mismas semillas para comparar los perfiles, conservando posiciones iniciales y focos. La frecuencia cambia cuándo ocurren los eventos de incendio. Los resultados se guardaron en carpetas separadas con manifiestos y huellas del código y mapas.

## Observaciones

Las siguientes medias dan igual peso a cada corrida y mezclan dos algoritmos, tres poblaciones y dos semillas (12 observaciones por mapa y perfil). Son un resumen para calibración, no una comparación estadística entre algoritmos.

| Mapa | Supervivencia media, k=3 | Supervivencia media, k=1 | Rango observado, k=1 |
| --- | ---: | ---: | ---: |
| bottleneck | 99.08 % | 65.88 % | 38.00–83.75 % |
| corporate_maze | 97.45 % | 62.99 % | 30.33–97.50 % |
| open_area | 96.35 % | 51.64 % | 30.00–81.25 % |

El perfil inicial produjo supervivencias próximas al techo en la mayoría de los casos. Con fuego cada turno aparecieron pérdidas más variadas sin hacer que todas las ejecuciones fueran inviables. El mayor número de turnos ejecutados fue 158 en el perfil inicial y 113 en el de fuego frecuente: duraciones menores pueden deberse a fallecimientos, no a mejores evacuaciones.

Las diferencias entre semillas son importantes. Dos semillas por configuración no permiten concluir significancia ni caracterizar de forma fiable toda la distribución.

## Parámetros comunes fijados para la siguiente etapa

Se seleccionó **k=1**, manteniendo probabilidad **0.4**, **dos focos**, capacidad **4** en pasillos y **2** en salida, y máximo de **1000 turnos**. Alpha queda en **1.0** y el umbral base en **3**. La elección busca evitar un escenario casi siempre resuelto por todos, sin optimizar parámetros para favorecer a BFS o A*.

Las capacidades y el máximo de turnos se conservaron; no se realizó una búsqueda exhaustiva sobre ellos. Ninguna corrida alcanzó el límite, por lo que no hubo truncamiento en este piloto. Eso no garantiza que otras estrategias tampoco alcancen el límite.

Estos parámetros están escritos explícitamente en `configs/benchmark_final.json`, sin cambiar los valores predeterminados del motor. Deben permanecer iguales para todos los algoritmos del experimento final. Cualquier revisión posterior debe documentarse y emplear una nueva carpeta de resultados.

## Configuración final preparada, no ejecutada

`configs/benchmark_final.json` reserva semillas 10000–10079 para BFS, UCS, A*, IDA* y genético. Con tres mapas y tres poblaciones son **3600 corridas**. Para alcanzar 200 repeticiones se deberá ampliar la lista antes de comenzar, usando una nueva salida si ya existen resultados.

La configuración referencia `results/policies/mejor.json`, todavía pendiente de producir mediante entrenamiento. El ejecutor rechaza iniciar esa matriz si falta la política; no inventa parámetros ni entrena automáticamente. Usar semillas de entrenamiento distintas de las piloto y de las finales (por ejemplo, 1000–1099).

No se midió ni validó la viabilidad computacional de IDA* en estos mapas. Su presencia en la configuración final no implica que se haya ejecutado en el piloto.

## Archivos y verificaciones

- Datos individuales: `results/raw/piloto_inicial/resultados.csv` y `results/raw/piloto_fuego_frecuente/resultados.csv`.
- Resumen preliminar: `results/summary/piloto_calibracion.csv`.
- Cada carpeta conserva 36 puntos de guardado completos y su `manifiesto.json`.
- Se comprobó la reanudación real del primer piloto: no repitió sus 36 corridas.
- Pasaron 43 pruebas unitarias y de integración, incluidas interrupción, reanudación, cambios de configuración, archivos corruptos y separación de semillas del genético.

Durante la preparación se corrigieron llamadas del motor que ignoraban validaciones con resultado `None`. Los validadores conservan esa convención; el constructor ahora detecta el fallo y evita iniciar una población parcial o una configuración inválida.

Las instrucciones del ejecutor están en [benchmark.md](benchmark.md). La agregación estadística final y los gráficos siguen pendientes.
