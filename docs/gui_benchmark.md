# GUI del benchmark

La ventana permite configurar y ejecutar experimentos. No entrena la política genética ni anima la evacuación.

## Abrir

Desde la raíz del proyecto, en una sesión con escritorio gráfico:

```bash
python3 -m src.gui.benchmark_app
```

Usa Tkinter y el ejecutor existente, con Python 3.11 o superior y NumPy. Tkinter está disponible en el entorno de desarrollo, aunque este no dispone de una pantalla accesible. Si tu instalación de Python no incluye Tkinter, necesitarás el paquete de Tk correspondiente a esa instalación. El ejecutor actual usa `fcntl`, por lo que esta versión está orientada a Linux/macOS.

## Preparar un experimento

1. En **Experimento**, marca los algoritmos que quieras ejecutar. Puedes elegir solo uno. El botón **Marcar todos** selecciona los siete: BFS, DFS, UCS, A*, IDA*, Greedy y genético.
2. Agrega o quita mapas. Se ejecutan todos los mapas de la lista; resaltar uno sirve para quitarlo, no para limitar la ejecución a ese mapa.
3. Indica poblaciones separadas por comas, por ejemplo `80, 180, 300`. Las semillas admiten listas o rangos: `10000-10079`. El modo final exige al menos 80 semillas; para pruebas pequeñas usa piloto.
4. En **Parámetros**, modifica capacidades, focos, frecuencia y probabilidad de fuego, límite de turnos, alpha y umbral de bloqueo. Los parámetros físicos se mantienen iguales entre algoritmos. Los pesos y el umbral del genético provienen de su archivo entrenado.
5. En **Modelo y resultados**, selecciona el JSON de la política entrenada y una carpeta de salida. Solo se exige un modelo si el genético está seleccionado.

La ventana carga inicialmente `configs/benchmark_final.json`, con los cinco algoritmos principales. El contador muestra el producto de mapas, poblaciones, semillas y algoritmos seleccionados.

**Ejecutar selección / Reanudar** ejecuta exactamente los algoritmos marcados. **Ejecutar todos (7)** marca todos y comienza, usando los demás campos actuales; no omite IDA* ni el genético. Si falta el modelo entrenado, muestra un error y no inicia un benchmark parcial.

## Guardar y recuperar configuraciones

**Guardar configuración** exporta un JSON compatible con la CLI. Permite preparar la configuración antes de disponer del modelo entrenado; la existencia y validez del modelo se comprueban al ejecutar.

**Cargar configuración / manifiesto** acepta configuraciones y `manifiesto.json` de un benchmark previo. Al cargar un manifiesto se recuperan los parámetros, el orden de algoritmos y semillas, y la carpeta de resultados.

Para continuar un trabajo previo, conserva la misma configuración, código, mapas y modelo. El ejecutor rechaza mezclar versiones o parámetros. Si haces cambios, usa **Usar nueva carpeta con fecha** o elige otra carpeta. Los pilotos históricos permanecen intactos: su código registrado puede ser distinto del actual y eso impide reanudarlos con la versión nueva.

## Progreso, detención y datos

El benchmark corre en un proceso separado; la ventana sigue respondiendo. Los campos se bloquean durante la ejecución para evitar que cambien los parámetros a mitad de un lote.

La barra indica corridas completas, no el avance interno de una búsqueda. Una corrida larga puede dejar la barra sin cambios hasta finalizar. El registro muestra resultados y errores del ejecutor.

**Detener y conservar avances** envía una interrupción al proceso. Se conservan los resultados de las corridas completas; la corrida interrumpida se repetirá al reanudar. Cerrar la ventana mientras trabaja ofrece detenerlo y espera su finalización antes de cerrar.

Se generan los mismos archivos de la CLI:

- `resultados.csv`: una fila por corrida completa.
- `corridas/`: puntos de guardado individuales.
- `manifiesto.json`: configuración y huellas de reproducibilidad.
- `progreso.json`: resumen de ejecuciones completas y pendientes.
- `errores/`: diagnósticos de corridas fallidas, cuando corresponda.

No se genera una política genética ficticia, no se ejecuta entrenamiento automáticamente y no se producen gráficos estadísticos en esta versión.

## Verificación

Se probaron selección individual y completa, edición y validación, lectura de configuraciones y manifiestos, y el proceso real de ejecución, reanudación, interrupción y modelo faltante.

Las dos pruebas de widgets se ejecutan cuando Tk puede abrir una pantalla. En este entorno fueron omitidas porque `DISPLAY=:1` no es accesible; no se realizó una comprobación visual de la ventana.
