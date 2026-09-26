# Decisiones metodológicas: Escape de la Torre

Fecha de actualización: 26 de septiembre de 2026.

Este documento registra las decisiones discutidas y el estado del código para preparar el informe. No presenta resultados experimentales: el motor y el ejecutor están implementados y existe una calibración piloto; falta entrenar la política definitiva y ejecutar el benchmark final. Se distingue entre decisiones implementadas, diseño previsto y asuntos pendientes.

## 1. Objetivo y requisitos del enunciado

Se busca comparar estrategias para evacuar personas de un piso con una única salida, obstáculos, congestión y propagación irreversible del fuego. Las acciones admitidas son movimientos ortogonales y espera.

El enunciado exige dos búsquedas no informadas, dos búsquedas informadas con heurísticas admisibles y un algoritmo genético propio. La comparación debe usar supervivencia y turnos de despeje, con al menos 80 repeticiones por combinación experimental; se esperan 200. La interfaz gráfica es opcional.

Las dimensiones concretas, capacidades, función de congestión y representación de datos son elecciones del proyecto, no valores impuestos por el enunciado.

## 2. Representación del mapa — implementada

El mapa se carga desde texto mediante `cargar_mapa(path)`, en `src/models/mapa.py`. Se devuelve una matriz NumPy con `dtype=object`: cada posición contiene una instancia diferente de `Celda`.

Se eligió una función de carga en lugar de una clase `Mapa` para mantener sencilla la implementación inicial. Las coordenadas son `(fila, columna)`, con índices desde cero. Se puede consultar una posición directamente, sin recorrer toda la matriz.

| Símbolo | Terreno | Capacidad actual |
| --- | --- | --- |
| `#` | Muro | 0 |
| `.` | Celda transitable | 4 |
| `E` | Salida | 2 |

El cargador conserva estas capacidades por defecto y el motor permite configurarlas por escenario. Son provisionales y deberán calibrarse. Se decidió usar la capacidad de la salida como máximo de admisiones por turno, sin caudal adicional.

Los escenarios previstos son grillas de 50 × 50:

- `maps/bottleneck.txt`: pasillos estrechos y cuello de botella; aproximadamente 38 % de muros.
- `maps/corporate_maze.txt`: laberinto de densidad intermedia; aproximadamente 28 % de muros.
- `maps/open_area.txt`: área abierta; aproximadamente 13 % de muros.

Las dimensiones y conectividad se comprobaron en una revisión anterior. El cargador valida archivo no vacío, filas uniformes, símbolos y unicidad de salida. No exige dimensiones 50 × 50 para permitir mapas pequeños de prueba.

NumPy se utiliza como contenedor de la grilla, sin atribuirle aceleración numérica automática sobre objetos Python. `mapa.copy()` comparte las instancias de `Celda`; para cada experimento se deberán construir celdas y agentes nuevos.

## 3. Celdas — implementadas

`src/models/celda.py` contiene:

- `simbolo`: terreno original.
- `capacidad`: máximo de agentes permitido.
- `agentes`: lista de objetos `Agente` presentes.
- `quemada`: indicador booleano del incendio.
- `quemar()`: cambia `quemada` a `True`.

El terreno y el incendio permanecen en atributos separados. Una salida incendiada sigue identificándose como salida, aunque deje de ser transitable. El estado del fuego se almacena en las celdas; por ahora no existe una segunda colección independiente de celdas quemadas.

El método `quemar()` no propaga el fuego ni registra fallecimientos. Esas responsabilidades corresponden al motor. Tampoco la lista de ocupantes impone por sí misma el límite de capacidad.

## 4. Agentes y transiciones — implementados

`src/models/agente.py` representa cada persona con identificador, fila, columna y estado. El enumerado `State` contiene `ACTIVO`, `ESPERANDO`, `EVACUADO` y `MUERTO`.

También se almacenan ruta, turno de evacuación, turno de fallecimiento, movimientos, esperas, turnos consecutivos bloqueado y replanificaciones. Los métodos permiten consultar posición y próximo paso, asignar o borrar ruta y cambiar estado.

Convenciones aplicadas por el motor:

- `ACTIVO` y `ESPERANDO` representan personas vivas dentro del mapa. Ambas ocupan capacidad y pueden ser alcanzadas por el fuego.
- Esperar no es un estado terminal; el agente debe poder volver a moverse.
- Las celdas conservarán únicamente ocupantes vivos no evacuados. Los demás permanecerán en una colección general para calcular métricas.
- Cada movimiento actualizará la posición del agente y las listas de origen y destino de forma consistente.
- Un paso se retira de la ruta únicamente después de ejecutarse. Un rechazo conserva ese paso.
- Una espera voluntaria y un bloqueo suman una espera, pero solo el bloqueo incrementa el contador de turnos bloqueado.

`asignar_ruta()` copia la lista recibida y aumenta `replanificaciones`. El motor cuenta exactamente una vez cada intento, incluidos el inicial y los fallidos; estos últimos asignan una ruta vacía. El resultado agregado usa el nombre `planificaciones`. El contador de bloqueo se reinicia al buscar y al moverse.

## 5. Contrato de planificación — implementado

Las búsquedas reciben la matriz y una posición inicial. UCS, A* e IDA* reciben además `alpha`, cuyo valor predeterminado es 1.0.

Devuelven una lista de próximos pasos, excluyendo el inicio e incluyendo la salida; `[]` si el agente ya está en la salida; o `None` si no devuelven ruta. Algunas validaciones de entrada también devuelven `None`, por lo que ese valor no distingue actualmente un problema inválido de uno sin solución.

Los algoritmos consultan celdas, pero no mueven agentes, propagan fuego ni cambian el mapa. El motor mantiene el mapa estable durante las búsquedas y recoge las propuestas antes de aplicar movimientos.

No hay una clase de snapshot: la estabilidad de la vista del entorno depende del orden de ejecución del motor.

## 6. Algoritmos de búsqueda — implementados

| Algoritmo | Criterio | Papel previsto |
| --- | --- | --- |
| BFS | Cola FIFO; explora por cantidad de pasos | No informado principal |
| UCS | Menor costo acumulado `g` | No informado principal |
| DFS | Pila LIFO; profundiza por una rama | Línea base adicional |
| A* | Menor `g + h` | Informado principal |
| IDA* | Profundidad con umbrales sucesivos de `g + h` | Informado principal |
| Greedy | Menor `h`, sin considerar `g` | Línea base adicional |

BFS minimiza pasos en el problema estático de movimientos unitarios, pero no el costo variable de congestión. DFS y Greedy no garantizan rutas mínimas.

UCS y A* usan colas de prioridad de `heapq`; esta biblioteca implementa la estructura de datos, no el algoritmo de búsqueda completo. IDA* tiene una búsqueda propia con pila explícita para evitar el límite de recursión de Python. No llama a A*. El nuevo umbral de IDA* es la menor estimación que excedió el umbral anterior.

El orden de vecinos es arriba, abajo, izquierda y derecha. DFS los inserta en orden inverso en su pila. Las colas de prioridad usan un contador de inserción para resolver empates de manera reproducible.

En la revisión de rendimiento, IDA* incorporó preparación del grafo alcanzable y una tabla de mejores costos que se reinicia en cada umbral. Esta variante usa memoria adicional O(V+E), conserva Manhattan y los umbrales de IDA*, y no llama a A*. El motor también reutiliza búsquedas idénticas dentro del mismo turno. Las decisiones, comprobaciones y limitaciones están en [revision_busquedas.md](revision_busquedas.md).

Las funciones Manhattan están repetidas en los tres archivos informados. Extraerlas a un módulo común es una mejora posible, todavía no realizada.

## 7. Congestión y heurística — implementadas en la planificación

UCS, A* e IDA* aplican el costo de entrada a la celda destino:

```text
ocupación = cantidad de agentes presentes en la celda
costo_paso = 1 + alpha × (ocupación / capacidad)²
```

Se requiere `alpha` finito y no negativo, y capacidad positiva para evaluar la división. UCS, A* e IDA* comprueban ambas condiciones de `alpha`. Las seis búsquedas rechazan celdas con capacidad no positiva.

La ocupación se obtiene mediante `len(celda.agentes)`, por lo que el motor deberá retirar evacuados y fallecidos. El costo se calcula con la ocupación observada, sin sumar anticipadamente al agente que está planificando.

Una celda llena no se descarta en la búsqueda solo por su ocupación: puede desocuparse antes de la llegada. La capacidad efectiva se resolverá durante la ejecución de movimientos. La fórmula modifica la preferencia de rutas; no convierte automáticamente un movimiento en varios turnos. El retraso físico previsto provendrá de esperas y restricciones de capacidad.

La heurística utilizada es Manhattan:

```text
h = abs(fila - fila_salida) + abs(columna - columna_salida)
```

Es admisible porque solo se permiten pasos ortogonales y cada paso cuesta al menos 1. Los obstáculos y penalizaciones no reducen ese límite inferior. El fuego actual se trata como bloqueo, no como penalización de riesgo futuro. Las búsquedas base no incluyen riesgo futuro; la variante de la política genética sí incorpora proximidad al fuego.

La optimalidad de UCS, A* e IDA* se refiere al problema estático que reciben al planificar. No garantiza maximizar supervivencia ni minimizar el tiempo global de evacuación de varios agentes.

## 8. Turnos y movimiento — implementados

El motor separa propuesta, resolución y aplicación. Cada turno propaga fuego, registra bajas, replanifica sobre una ocupación estable, resuelve solicitudes, aplica movimientos y registra evacuaciones y esperas.

Por decisión del usuario se permite entrar únicamente al espacio libre después de las bajas y antes de los movimientos. No se aprovecha el espacio que otro agente libera durante el mismo turno. Los intercambios entre celdas llenas se rechazan. Los conflictos se resuelven con sorteos reproducibles partiendo de IDs ordenados.

La entrada a la salida evacúa inmediatamente. Su capacidad limita las admisiones del turno, sin un caudal adicional; retirar evacuados no reutiliza cupos ese turno. Cada agente realiza como máximo un movimiento ortogonal.

Las búsquedas no planifican esperas futuras. El motor hace esperar ante ausencia de ruta o movimiento rechazado. Sin ruta se reintenta el próximo turno. Las búsquedas normales replanifican también por rutas inválidas o tres turnos de bloqueo, configurable; el genético usa su propio umbral.

La inicialización, interfaces, valores configurables y ejemplo ejecutable están en [motor_simulacion.md](motor_simulacion.md).

## 9. Fuego integrado y registro de bajas

`src/simulation/fuego.py` permite seleccionar focos iniciales reproducibles o indicar posiciones manualmente. Los focos son distintos y excluyen muros, salida, celdas ya quemadas y celdas con agentes. No se generan focos espontáneos después del turno cero.

La propagación ocurre en turnos positivos múltiplos de `k`. Cada celda sana transitable con al menos un vecino ortogonal quemado recibe un único intento por evento, con probabilidad configurable entre cero y uno. Tener varios vecinos quemados no aumenta esa probabilidad. Los intentos fallidos pueden repetirse en eventos posteriores.

Primero se identifican las candidatas a partir del fuego existente, luego se realizan sorteos en orden fijo y finalmente se aplican los incendios. El frente avanza como máximo una celda por evento. Los muros bloquean el fuego; la salida y las celdas ocupadas pueden incendiarse por propagación.

El generador de propagación se crea una vez por ejecución, se reutiliza y permanece separado de inicialización, movimientos y genético. La propagación no depende de la ocupación. El motor llama a esta función una sola vez por turno y mantiene los mismos focos y semillas entre algoritmos con igual configuración.

El módulo devuelve las posiciones recién quemadas. El motor registra bajas y retira agentes antes de planificar o mover. Las rutas incendiadas se invalidan y recalculan en el mismo turno. Las celdas mantienen el estado irreversible del incendio.

No existen todavía humo ni colapso estructural. Los valores de cantidad de focos, frecuencia y probabilidad deben calibrarse antes del benchmark. Se incorporaron pruebas de frecuencia, irreversibilidad, ausencia de cascadas, un intento por celda, reproducibilidad y separación de responsabilidades.

## 10. Algoritmo genético — conectado; entrenamiento experimental pendiente

Se implementó una política global con tres genes: peso de congestión, peso de riesgo de incendio y umbral de turnos bloqueado para replanificar. La política usa una variante de A*; el A* base permanece independiente. El riesgo se define como `1 / (1 + distancia Manhattan al fuego más cercano)`, o cero sin fuego. No representa una probabilidad de incendio ni incorpora el efecto de los muros.

La evolución incluye selección por torneo, cruce uniforme, mutación gaussiana de pesos, mutación entera del umbral y elitismo. La aptitud inicial es solo supervivencia promedio, dando igual peso a cada ejecución. Los rangos y parámetros predeterminados son provisionales y deben fijarse antes del entrenamiento final.

El entrenamiento recibe una función de simulación y reserva semillas separadas para evaluación. Guarda parámetros, aptitud, configuración e historial en JSON. La conexión al motor se comprobó mediante un entrenamiento diminuto de prueba. Todavía no hay una estrategia ganadora validada mediante experimentos finales. Los genes modifican preferencias, nunca capacidades físicas o reglas del fuego.

El contrato de integración, los archivos y las pruebas se describen en [modelo_genetico.md](modelo_genetico.md).

## 11. Diseño experimental y reproducibilidad — ejecutor y piloto implementados

Se habían propuesto poblaciones de 80, 180 y 300 agentes, con pocas repeticiones durante desarrollo y entre 80 y 200 para cada configuración final. Los valores finales deberán fijarse tras pruebas piloto y quedar registrados antes del benchmark.

Para una repetición dada, todos los algoritmos deben compartir mapa, capacidades, posiciones iniciales, focos y realización del fuego. Se recomienda usar fuentes aleatorias independientes para inicialización, incendio, conflictos y entrenamiento genético. Una única semilla con un generador compartido no asegura incendios equivalentes si los algoritmos consumen números aleatorios en distinto orden.

Se deberán guardar parámetros, semillas, versión del código y resultados por ejecución. Los escenarios se reconstruirán desde cero para no arrastrar fuego, rutas ni ocupantes de otra repetición.

La condición de término es ausencia de agentes vivos dentro del mapa o máximo de turnos. Los agentes vivos al alcanzar el límite se registrarán como pendientes, no automáticamente como fallecidos.

## 12. Métricas por ejecución implementadas; agregación pendiente

Métricas obligatorias:

- Supervivencia: `100 × evacuados / población inicial`.
- Tiempo de despeje: turno en que llega el último evacuado.
- Media, desviación estándar, mínimo y máximo del tiempo de despeje por configuración.

Se propone registrar el tiempo como ausente si nadie evacúa, e informar por separado cuántas ejecuciones presentan ese caso. No debe asignarse cero como si fuera una evacuación rápida. Las estadísticas temporales deberán indicar cuántas observaciones válidas usan y distinguir ejecuciones truncadas por el máximo de turnos.

Métricas complementarias previstas: fallecidos, pendientes al cierre, movimientos, esperas, replanificaciones, congestión acumulada y cantidad de ejecuciones que alcanzan el límite. La fórmula de congestión acumulada y la convención de desviación estándar aún deben fijarse.

Supervivencia y tiempo deben analizarse juntos: evacuar a pocas personas rápidamente puede producir un tiempo bajo sin representar un buen resultado. El tiempo de cómputo puede registrarse como información secundaria, pero no sustituye los turnos de simulación.

## 13. Interfaz gráfica — opcional y pendiente

La matriz de celdas es compatible con una futura interfaz. El motor actualizará los datos y la vista dibujará terreno, fuego y ocupantes. No se incorporarán componentes gráficos dentro de `Celda` o `Agente`.

La velocidad de animación será independiente de los turnos. Los benchmarks se ejecutarán sin renderizado. PySide6 fue una opción inicial; no hay interfaz ni dependencia gráfica incorporada actualmente.

## 14. Verificación y límites actuales

Durante la incorporación inicial de A*, Greedy e IDA* se verificaron rutas en pequeños escenarios, integración con NumPy, casos límite y caminos de 1100 pasos. A* e IDA* coincidieron en costo con UCS en 50 escenarios pequeños. Estas comprobaciones se ejecutaron mediante un script temporal; no constituyen un benchmark de evacuación ni una batería de pruebas persistente del repositorio.

El código recibió ajustes posteriores; habrá que repetir y conservar pruebas antes del experimento final. También se debe comprobar movimiento simultáneo, capacidades, fuego, consistencia entre posiciones y ocupantes, reproducibilidad y métricas.

IDA* puede repetir muchas expansiones, especialmente con costos variables o salidas inaccesibles. No hay límites de búsqueda implementados. Si se introducen, habrá que distinguir interrupción de búsqueda y ausencia de ruta, y reportar su uso.

## 15. Próximos pasos y trazabilidad del informe

1. Entrenar el genético con semillas distintas de las piloto y finales.
2. Ejecutar la matriz final con los parámetros comunes fijados.
3. Implementar agregación estadística final y preparar tablas y figuras.

El informe deberá registrar las decisiones finales, parámetros efectivos, resultados, limitaciones y referencias. Se utilizó asistencia de IA generativa para discutir el diseño, proponer modelos y búsquedas, e implementar inicialmente A*, Greedy e IDA* con verificaciones. Este apoyo deberá declararse según el enunciado, precisando las revisiones y modificaciones realizadas por el equipo. No se han empleado bibliotecas que resuelvan directamente estas búsquedas.

## 16. Verificación de integración del motor

Se incorporaron pruebas de evacuación con las seis búsquedas y el genético, conflictos, capacidades, fuego, bajas, replanificación, reproducibilidad y entrenamiento diminuto con el motor real. Estos casos controlados no sustituyen el benchmark sobre mapas oficiales. El motor expone avance por turno y ejecución completa sin interfaz gráfica. Los límites computacionales de IDA* siguen vigentes.

## 17. Ejecutor y calibración piloto

Se implementó un ejecutor secuencial con guardado atómico por corrida, CSV y reanudación verificada contra configuración, código, mapas y política. El modo final exige al menos 80 semillas por configuración. Los fallos no se contabilizan como cero supervivencia y se reintentan al reanudar.

Se completaron 72 corridas piloto con BFS/A*, tres mapas, tres poblaciones y semillas 100–101. Se seleccionó fuego cada turno (`k=1`) con probabilidad 0.4, manteniendo dos focos, capacidades 4/2 y máximo de 1000 turnos. Los valores por defecto del motor permanecen como estaban; la configuración experimental los fija explícitamente. No se observaron corridas truncadas en el piloto.

La configuración final reserva semillas 10000–10079 y requiere una política genética entrenada que aún no existe. No se ejecutó el benchmark final ni se realizó la comprobación de rendimiento de IDA*, según lo solicitado. Los resultados y limitaciones de la calibración están en [calibracion_piloto.md](calibracion_piloto.md).
