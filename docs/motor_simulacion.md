# Motor de simulación

El motor permite avanzar un turno o ejecutar una evacuación completa sin interfaz gráfica. Usa las celdas y agentes existentes, las seis búsquedas y la política genética.

## Ejemplo desde la raíz del repositorio

Se requiere Python y NumPy. Ejecutar desde la carpeta que contiene `src/` y `maps/`:

```bash
python3 - <<'PY'
from src.simulation.motor import MotorSimulacion

escenario = {
    "mapa": "maps/open_area.txt",
    "poblacion_inicial": 80,
    "cantidad_focos": 2,
    "k": 3,
    "probabilidad": 0.4,
    "max_turnos": 150
}

motor = MotorSimulacion("bfs", escenario, semilla=42)
print(motor.ejecutar())
PY
```

Para observar el estado por turnos:

```python
motor = MotorSimulacion("a_star", escenario, semilla=42)
while not motor.terminada:
    resultado = motor.avanzar_turno()
    print(motor.turno, resultado)
    # motor.mapa y motor.agentes están disponibles para una futura interfaz.
```

`resultado()` consulta sin avanzar. Llamar a `avanzar_turno()` o `ejecutar()` después del término no modifica el estado. No editar el mapa ni los agentes externamente durante una ejecución.

## Configuración

| Campo | Valor inicial | Significado |
| --- | --- | --- |
| `mapa` | Obligatorio | Ruta a un archivo de texto; las rutas relativas se resuelven desde el directorio de ejecución. |
| `poblacion_inicial` | Obligatorio | Entero positivo. |
| `capacidad_pasillos` | 4 | Capacidad por celda `.`. |
| `capacidad_salida` | 2 | Máximo de admisiones a `E` por turno. |
| `cantidad_focos` | 2 | Focos iniciales aleatorios. Cero desactiva la ignición inicial. |
| `k` | 3 | Frecuencia de propagación en turnos positivos. |
| `probabilidad` | 0.4 | Probabilidad por celda candidata y evento. |
| `max_turnos` | 1000 | Límite de turnos, no de tiempo computacional. |
| `alpha` | 1.0 | Congestión en UCS, A* e IDA*, al seleccionar una búsqueda por nombre. |
| `umbral_bloqueo` | 3 | Turnos bloqueado para replanificar en búsquedas normales. |
| `posiciones_iniciales` | Opcional | Lista de `[fila, columna]`, una por agente; admite posiciones repetidas dentro de la capacidad. |
| `focos` | Opcional | Lista de posiciones distintas; `[]` significa sin focos. |

Si se especifican `focos` y `cantidad_focos`, deben coincidir. Las posiciones iniciales no pueden ser muros, salida ni fuego. Los parámetros desconocidos se rechazan para detectar errores de escritura.

Los nombres de búsquedas son `bfs`, `dfs`, `ucs`, `a_star`, `ida_star` y `greedy`. También se acepta un objeto `PoliticaBusqueda` o `PoliticaGenetica`. Cuando se proporciona un objeto, sus parámetros de planificación prevalecen; `alpha` y `umbral_bloqueo` del escenario solo configuran la selección por nombre.

Estos valores son iniciales para desarrollo. No deben presentarse como parámetros experimentales calibrados.

## Inicialización reproducible

Cada ejecución carga nuevas celdas y crea nuevos agentes y una copia de la política. La semilla principal deriva cuatro semillas independientes, en orden fijo: focos, posiciones, fuego y conflictos. La evolución genética usa su propio generador fuera del motor.

Con posiciones automáticas, se encienden primero los focos y luego se seleccionan espacios de ocupación sin reemplazo; una celda puede contener varios agentes hasta su capacidad. Con posiciones manuales, se reservan primero esas posiciones para excluirlas de los focos aleatorios. Los focos manuales que coincidan con agentes se rechazan.

`motor.focos`, `motor.posiciones_iniciales`, `motor.semillas` y `motor.escenario` permiten inspeccionar las condiciones efectivas. Distintos algoritmos con el mismo escenario y semilla reciben las mismas posiciones, focos y evolución del incendio durante los turnos comunes. La cantidad de conflictos no altera el generador del fuego.

## Orden y reglas de los turnos

1. Propagar fuego, como máximo una vez por turno.
2. Registrar fallecimientos y retirar esos agentes de la ocupación.
3. Replanificar sobre el mismo mapa y ocupación para todos los agentes.
4. Recoger solicitudes y asignar espacios disponibles por destino.
5. Retirar los movimientos aceptados de sus orígenes y aplicar sus destinos.
6. Registrar esperas, evacuaciones y término.

Se usa solo el espacio libre después de las bajas y antes de cualquier movimiento. Las salidas de otros agentes no crean espacios utilizables ese turno. Por ello los intercambios entre celdas llenas se rechazan; los bloqueos que esto genere forman parte del modelo elegido.

Ante exceso de solicitudes se sortean ganadores partiendo de IDs ordenados y procesando destinos en orden fijo. Cada agente se mueve como máximo una celda ortogonal. La lista de pasos solo avanza cuando se acepta el movimiento.

La entrada a `E` evacúa inmediatamente y no deja ocupación persistente. Las admisiones se aprueban una sola vez: retirar evacuados no abre nuevos cupos durante el mismo turno. No hay un caudal adicional separado de la capacidad de la salida.

Las búsquedas normales replanifican al faltar una ruta, invalidarse un paso o alcanzar el umbral de bloqueo. La política genética usa su propio umbral. Una búsqueda reinicia `turnos_bloqueado`; un rechazo posterior lo incrementa. Sin ruta se espera y se vuelve a buscar el siguiente turno, sin registrar un bloqueo por capacidad.

El campo existente `agente.replanificaciones` cuenta todos los intentos de planificación, incluidos el inicial y los fallidos. En el resultado agregado se denomina `planificaciones`. Se incrementa exactamente una vez por intento.

## Resultados

`ejecutar()` y `simular()` devuelven un diccionario con:

- `evacuados`, `fallecidos` y `pendientes`, cuya suma conserva la población inicial.
- `supervivencia`, fracción entre 0 y 1; multiplicar por 100 para expresarla en porcentaje.
- `turnos_ejecutados` y `turno_ultimo_evacuado` (ausente mediante `None` si nadie evacuó).
- `motivo_termino`: `sin_agentes_pendientes` o `max_turnos`; antes de terminar es `None`.
- Totales de `movimientos`, `esperas` y `planificaciones`.

Los vivos al alcanzar el límite permanecen pendientes, no se convierten en fallecidos. No se termina anticipadamente por ausencia de ruta. Si todos finalizan exactamente en el último turno permitido, prevalece `sin_agentes_pendientes`.

## Conexión al genético

La función puede pasarse directamente al entrenamiento:

```python
from src.simulation.motor import simular
from src.evaluation.train_genetic import entrenar

mejor, historial = entrenar(
    simular=simular,
    escenarios=[escenario],
    semillas_entrenamiento=[1, 2],
    semillas_evaluacion=[100, 101],
    archivo_salida="results/policies/mejor.json",
    configuracion={"tamano_poblacion": 3, "generaciones": 2}
)
```

No confundir el ejemplo de integración con un entrenamiento o benchmark final. IDA* puede tardar mucho en búsquedas complejas: `max_turnos` no interrumpe una búsqueda en curso. Las pruebas de todos los algoritmos usan mapas pequeños; todavía se requiere calibración y medición sobre los mapas oficiales.

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```

Se comprueban capacidades, espacio inicial, salida, fuego, bajas, replanificación, reproducibilidad, errores de configuración y un entrenamiento diminuto con el motor real. Las pruebas del módulo de fuego conservan su contrato actual de `None` ante parámetros inválidos; el motor transforma esos fallos en errores explícitos.
