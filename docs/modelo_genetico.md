# Modelo genético

Implementación inicial del 26 de septiembre de 2026. El optimizador, la política y el motor están implementados y conectados. Se probó un entrenamiento diminuto de integración; el entrenamiento experimental está pendiente. Los valores predeterminados sirven para desarrollo, no constituyen parámetros calibrados.

## Individuo y política

Cada `Individuo` representa una estrategia global con tres genes:

| Gen | Rango inicial | Uso |
| --- | --- | --- |
| `peso_congestion` | 0 a 10 | Penaliza ocupación relativa al cuadrado. |
| `peso_riesgo` | 0 a 10 | Penaliza proximidad Manhattan al fuego. |
| `umbral_bloqueo` | 1 a 10, entero | Turnos bloqueado antes de replanificar. |

`PoliticaGenetica.planificar(mapa, inicio)` usa una variante de A* con:

```text
costo = 1 + peso_congestion × (ocupacion / capacidad)²
          + peso_riesgo × riesgo
riesgo = 1 / (1 + distancia Manhattan al fuego más cercano)
```

Sin fuego, el riesgo es cero. Las celdas incendiadas son intransitables. El riesgo no es una probabilidad ni contempla el efecto protector de los muros. La heurística sigue siendo Manhattan, admisible porque el costo mínimo por paso es 1. El A* base permanece sin cambios para permitir una comparación independiente.

La política devuelve rutas sin incluir el inicio, `[]` si ya está en la salida o `None` si no devuelve ruta. Consulta el mapa sin modificarlo. La ocupación debe permanecer estable durante la búsqueda; la capacidad física se aplica en el motor al ejecutar movimientos.

`necesita_replanificar(mapa, agente)` considera agentes activos y esperando. Replanifica si falta ruta, esta contiene pasos inválidos o fuego, no termina en la salida, o se alcanza el umbral de bloqueo. El motor debe procesar bajas y evacuaciones antes de consultar esta regla. El motor reinicia el contador de bloqueo en cada intento de planificación; un rechazo posterior comienza a contarlo nuevamente.

## Optimización

`evolucionar(evaluar, ...)` crea una población y aplica selección por torneo, cruce uniforme, mutación gaussiana de pesos, mutación del umbral en ±1 y elitismo. Las mutaciones quedan dentro de los rangos configurados. Los individuos se copian para no modificar a sus padres.

La aptitud es exclusivamente la supervivencia promedio entre 0 y 1. Cada ejecución tiene igual peso, aunque cambie la población inicial. No hay criterio temporal de desempate por ahora. Las generaciones cuentan poblaciones evaluadas, incluida la inicial. El historial registra mejor aptitud, promedio y mejores parámetros por generación.

La evolución usa su propio `random.Random(semilla)`, separado de la aleatoriedad del simulador.

## Conexión con el motor

`src/evaluation/train_genetic.py` expone:

```python
entrenar(
    simular,
    escenarios,
    semillas_entrenamiento,
    semillas_evaluacion,
    archivo_salida,
    configuracion=None
)
```

`simular` está implementada en `src.simulation.motor` con este contrato:

```python
from src.simulation.motor import simular

resultado = simular(politica, escenario, semilla)
# Incluye evacuados, fallecidos, pendientes y métricas por ejecución.
```

Cada escenario es un diccionario serializable a JSON que incluye `poblacion_inicial`; puede añadir mapa, parámetros del fuego y límite de turnos. Los tres conteos de salida deben ser enteros no negativos y sumar la población inicial. Los pendientes no cuentan como evacuados ni fallecidos.

Todos los individuos se evalúan con el mismo producto de escenarios y semillas de entrenamiento. Se crea una copia del escenario y una política nueva para cada llamada. El motor debe construir nuevas celdas y agentes, y garantizar el mismo incendio para cada escenario y semilla, independientemente de las decisiones de la política. Copiar un diccionario no sustituye este requisito del motor.

Las semillas de evaluación deben ser distintas y no se ejecutan durante el entrenamiento. Se reservan para el benchmark final. El JSON de salida guarda la estrategia elegida, aptitud de entrenamiento, configuración, escenarios, semillas e historial. Esa aptitud no debe presentarse como resultado de evaluación independiente.

El ejemplo de entrenamiento conectado al motor se describe en [motor_simulacion.md](motor_simulacion.md). Para importar estos módulos, ejecutar Python desde la raíz del repositorio y usar rutas de paquete, por ejemplo `from src.evaluation.train_genetic import entrenar`.

## Pruebas

Desde la raíz del repositorio:

```bash
python3 -m unittest discover -s tests -p 'test_genetico.py' -v
```

Las pruebas verifican rutas, costo óptimo de la política en un caso controlado, reacción al riesgo, replanificación, rangos de genes, copias, elitismo, reproducibilidad, promedio de tasas y separación de semillas. Los simuladores usados en estas pruebas son dobles de prueba con resultados controlados: no son un motor de evacuación ni producen evidencia experimental de supervivencia.
