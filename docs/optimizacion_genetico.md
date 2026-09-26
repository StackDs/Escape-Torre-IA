# Optimización del entrenamiento genético

Se mantienen los genes, la aptitud, las semillas y los operadores de evolución. Las mejoras reducen trabajo repetido sin disminuir mapas, agentes, semillas o generaciones.

## Riesgo compartido

La versión anterior encontraba el fuego más cercano comparando cada celda explorada con todas las celdas incendiadas. Su diccionario de riesgos duraba una sola búsqueda, por lo que otros agentes repetían el cálculo.

Ahora una búsqueda en anchura desde todas las celdas incendiadas calcula las distancias para la grilla completa. Este recorrido atraviesa también muros para conservar exactamente la definición geométrica de Manhattan; no representa propagación real del incendio. El riesgo sigue siendo `1 / (1 + distancia)`.

La política conserva esa tabla y la reutiliza entre agentes mientras coincidan dimensiones y posiciones incendiadas. Si cambia el fuego, la tabla se recalcula. La ocupación y la congestión siguen consultándose en cada búsqueda; no se reutilizan costos de congestión antiguos. Con peso de riesgo cero no se construye la tabla.

## Evaluaciones repetidas

Cada llamada a `entrenar()` conserva un diccionario de aptitudes por combinación exacta de los tres genes, sin redondeos. Si una élite o un hijo tiene genes ya evaluados, reutiliza su aptitud. Se mantienen el orden de selección, los sorteos y el historial de generaciones.

Esta reutilización requiere que el simulador produzca los mismos resultados con la misma política, escenario y semilla. Es el contrato del motor actual. Para comprobar equivalencia o usar un simulador que no cumpla ese contrato, puede llamarse `entrenar(..., reutilizar_evaluaciones=False)`.

La caché es propia de cada entrenamiento y no mezcla escenarios ni semillas de entrenamientos distintos. El JSON final añade `evaluaciones_individuos` con cantidades solicitadas, simuladas y reutilizadas. Las estadísticas cuentan estrategias; cada evaluación simulada implica todos los escenarios y semillas de entrenamiento.

## Ejecutar

Desde la raíz del proyecto:

```bash
python3 -u entrenar.py
```

El lanzador usa 10 individuos, 5 generaciones y semillas 1000, 1001 y 1002, con escenarios y parámetros leídos de `configs/benchmark_final.json`. Informa simulaciones realmente ejecutadas y el máximo posible sin reutilización. Puede terminar antes de alcanzar ese máximo.

```bash
python3 -u entrenar.py --poblacion 10 --generaciones 5 --semillas 1000 1001 1002 --salida results/policies/mejor.json
```

Para una ejecución futura en segundo plano:

```bash
mkdir -p results/logs
nohup python3 -u entrenar.py > results/logs/entrenamiento_optimizado.log 2>&1 < /dev/null &
```

Estas modificaciones no actualizan el código cargado por un entrenamiento que ya estaba ejecutándose. No se ha detenido ni reemplazado ese proceso. El nuevo lanzador no recupera su memoria: iniciarlo comienza otro entrenamiento.

La caché es de memoria y el modelo se sigue guardando al finalizar; esta optimización no incorpora reanudación ni puntos de guardado persistentes.

## Verificación

Las pruebas de `tests/test_optimizacion_genetica.py` comprueban igualdad exacta con la distancia Manhattan original, reutilización e invalidación del riesgo, cambios de ocupación, peso de riesgo cero e igualdad del mejor individuo e historial con y sin caché de aptitudes.

No se restauraron los archivos de pruebas que estaban eliminados en el espacio de trabajo. Se añadió una prueba específica para estas optimizaciones.

## Medición controlada

Se comparó la política anterior con la optimizada en `maps/open_area.txt`, con 80 agentes, semilla 1000, genes `[2, 5, 3]`, dos focos, `k=1`, probabilidad 0.4 y máximo de 200 turnos.

- Versión anterior: 39.6496 segundos.
- Versión optimizada: 2.0888 segundos.
- Aceleración observada: 18.98 veces.

Ambas devolvieron 43 evacuados y 37 fallecidos en 45 turnos de simulación, con último evacuado en el turno 39. También se compararon las rutas, posiciones y estados de todos los agentes en cada turno y fueron idénticos. Esta es una medición individual de ejecución completa, no una estimación garantizada de todo el entrenamiento. No incluye el ahorro adicional por reutilizar aptitudes de individuos repetidos.
