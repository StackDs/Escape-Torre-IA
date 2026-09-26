# Revisión de rendimiento de las búsquedas

Se revisaron las seis búsquedas del benchmark, su integración con el motor y el costo de replanificar. Las mediciones son diagnósticas; no representan las 200 semillas ni sustituyen el benchmark de supervivencia.

## Hallazgos por algoritmo

| Algoritmo | Revisión | Causa del costo |
| --- | --- | --- |
| BFS | Cola `deque`, visitados al descubrir, reconstrucción con padres. Minimiza pasos, sin penalización por congestión. | Explora las celdas alcanzables: O(V+E) por búsqueda. No se observó una repetición interna innecesaria. |
| DFS | Pila con visitados al descubrir; no se queda recorriendo ciclos. El orden de vecinos se mantiene. | Sus rutas pueden ser largas, incendiarse y provocar muchas replanificaciones. Menor costo de una búsqueda no implica menor costo de una evacuación completa. |
| UCS | Costos acumulados, prioridad por g y descarte de entradas obsoletas correctos. | Explora sin heurística y calcula congestión en cada transición. Puede visitar más celdas que A*. Se corrigió el rechazo de `NaN` e infinito en alpha. |
| A* | g incluye congestión; Manhattan es admisible y consistente para estos costos de paso, que son al menos 1. | Buscar la salida recorre el mapa en cada llamada; es un costo lineal, no una explosión de ramas. No se cambió su prioridad ni su desempate. |
| Greedy | Prioridad solo por Manhattan, visitados al descubrir y desempate por inserción. | Puede devolver rutas poco convenientes: no garantiza menor costo ni mayor supervivencia. No se detectó un problema de complejidad comparable al de IDA*. |
| IDA* | Antes evitaba ciclos solo dentro del camino actual. Otras ramas volvían a explorar la misma región y cada umbral repetía ese trabajo. | Combinación especialmente costosa con ciclos, congestión fraccionaria y salida desconectada por fuego. La implementación era completa en mapas finitos, pero podía tardar demasiado en terminar. |

V representa celdas transitables y E sus conexiones ortogonales. UCS, A* y Greedy utilizan colas de prioridad; BFS y DFS no las necesitan. El número de búsquedas del motor multiplica el costo de cada llamada.

## Cambios aplicados

### IDA*

1. Preparar los vecinos, costos de entrada y valores Manhattan una vez por llamada. La ocupación es estable durante la planificación.
2. Comprobar conectividad mientras se prepara ese grafo. Si no se alcanza la salida, devolver `None` sin recorrer umbrales. Esta exploración con pila no proporciona la ruta final.
3. Guardar el menor g de cada celda dentro del umbral. Descartar llegadas iguales o peores y reabrir la celda si se descubre un costo menor.
4. Vaciar esa tabla al subir el umbral, para poder explorar las ramas antes cortadas. El nuevo umbral sigue siendo el menor f que excedió el anterior.

Sigue siendo una búsqueda IDA* independiente y no llama a A*. Ahora es una variante con tabla de mejores costos y grafo preparado, con memoria adicional O(V+E), equivalente a O(V) en esta grilla de grado máximo cuatro. Ya no debe describirse como una implementación que almacena únicamente el camino. La validación comprueba costos óptimos; no establece equivalencia de todas las rutas empatadas con la implementación anterior ni de todas sus supervivencias.

No se añadieron límites de tiempo ni de expansiones al algoritmo de producción. Los costos variables todavía pueden generar muchos umbrales y reaperturas. La comprobación de conectividad también añade trabajo en búsquedas sencillas.

### Motor y validaciones

- Una ruta ya comprobada por el motor no se recorre otra vez en `PoliticaBusqueda.necesita_replanificar`.
- Agentes que buscan desde la misma celda durante la misma fase comparten el resultado de la búsqueda, incluido `None`. El mapa y la ocupación son idénticos para ellos.
- La memoria de rutas se descarta antes del siguiente turno; nunca reutiliza una ruta sobre otro estado del fuego o de congestión. Solo se aplica a la política estándar exacta, para respetar posibles políticas externas con estado propio.
- Cada agente recibe su propia copia y sigue sumando una planificación por intento. La métrica `planificaciones` cuenta solicitudes, no llamadas físicas después de reutilizar un resultado.
- BFS y DFS ahora también rechazan capacidad cero. Se corrigió el comentario de DFS: una pila es LIFO.

No se cambiaron poblaciones, fuego, costos, prioridades de movimientos, umbrales de bloqueo ni semillas.

## Verificación

`python3 -m unittest discover -s tests -q`

Se añadieron pruebas persistentes de contratos, no mutación, capacidad cero, salida quemada, alpha no finito, salida inaccesible con ciclos y un desvío con congestión. En 120 mapas pequeños reproducibles, A* e IDA* se comparan con UCS para distintos valores de alpha y ocupación.

Para las seis búsquedas se comparan resultados y estados de todos los agentes turno a turno entre el motor optimizado y una política sin reutilización, incluyendo incendio y conflictos. Una prueba verifica que `None` se comparte solo dentro de un turno y que se conservan los contadores por persona. Además, DFS se comparó contra el motor original en los tres mapas oficiales con 80 agentes y semilla 10000: los resultados y estados finales coincidieron.

## Interpretación y ejecución posterior

El ejecutor imprime progreso al completar cada simulación. Una búsqueda lenta puede dejarlo mucho tiempo sin mensajes. `max_turnos=1000` limita turnos simulados, no segundos de CPU ni expansiones dentro de una búsqueda.

El diagnóstico interrumpe algunas mediciones con una alarma externa para no ejecutar trabajo ilimitado. Esos casos se marcan como incompletos, con resultado ausente; no se guardan como muertes ni cero supervivencia en el benchmark. Los tiempos incluyen el motor completo, sin las exportaciones CSV/TXT del ejecutor.

Como cambió el código, una carpeta de benchmark iniciada con la versión anterior no se puede reanudar con esta versión. Para ejecutar el experimento revisado, usar una carpeta nueva:

```bash
python3 -u bench_sin_genetico.py --salida results/raw/bench_sin_genetico_200_revisado
```

No se lanzó el benchmark de 10800 simulaciones durante esta revisión.

## Mediciones locales finales

Una corrida por algoritmo y mapa, 80 agentes, semilla 10000, k=1 y probabilidad de propagación 0.4. Segundos de simulación completa después de los cambios. Son tiempos orientativos de esta máquina, sin repeticiones para cuantificar variabilidad. No deben extrapolarse directamente a 180/300 agentes o 200 semillas.

| Algoritmo | Bottleneck | Corporate maze | Open area |
| --- | ---: | ---: | ---: |
| bfs | 0.38 s | 0.54 s | 0.77 s |
| dfs | 4.81 s | 3.70 s | 5.70 s |
| ucs | 0.60 s | 0.78 s | 1.30 s |
| a_star | 0.30 s | 0.36 s | 0.51 s |
| greedy | 0.24 s | 0.30 s | 0.44 s |
| ida_star | 1.28 s | 3.06 s | 2.59 s |

Antes de los ajustes, IDA* seguía en el turno 1 al cortar a los 3 segundos en los dos primeros mapas; en el área abierta estaba en el turno 4. No se midió su duración total original, por lo que no se calcula un factor exacto de aceleración.

Los 12 resultados completos originales de BFS, UCS, A* y Greedy coinciden con los finales, en todas las métricas del motor. DFS también coincide en su comparación completa separada. No hay resultados completos originales de IDA* en estos mapas para comparar supervivencia.

Evidencia: [revision_busquedas.json](../results/profiling/revision_busquedas.json).
