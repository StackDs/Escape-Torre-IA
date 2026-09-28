# Escape de la Torre IA

Simulación multiagente y evaluación comparativa de algoritmos de búsqueda clásica e inteligencia artificial aplicados a la evacuación de emergencia en edificios ante la propagación estocástica de incendios.

---

## Tabla de Contenidos

- [Escape de la Torre IA](#escape-de-la-torre-ia)
  - [Tabla de Contenidos](#tabla-de-contenidos)
  - [Descripción del Proyecto](#descripción-del-proyecto)
  - [Dependencias y Requisitos](#dependencias-y-requisitos)
  - [Instalación](#instalación)
  - [Estructura del Proyecto](#estructura-del-proyecto)
  - [Uso del Programa](#uso-del-programa)
    - [Interfaz Gráfica Interactiva (GUI)](#interfaz-gráfica-interactiva-gui)
    - [Ejecución de Benchmarks Masivos](#ejecución-de-benchmarks-masivos)
    - [Entrenamiento del Algoritmo Genético](#entrenamiento-del-algoritmo-genético)
  - [Resumen Metodológico y Algoritmos](#resumen-metodológico-y-algoritmos)
  - [Uso Académico](#uso-académico)

---

## Descripción del Proyecto

El sistema modela un entorno discreto bidimensional ($50 \times 50$) donde una población de agentes (150 personas por defecto) debe evacuar hacia una única salida de emergencia mientras un incendio se propaga de manera estocástica e irreversible.

El objetivo es comparar empíricamente el rendimiento de diversas estrategias de navegación bajo restricciones físicas de congestión (capacidad máxima de 4 agentes por pasillo y 2 agentes por turno en la salida) y peligro térmico:

- **Búsquedas no informadas:** Breadth-First Search (BFS), Depth-First Search (DFS), Uniform Cost Search (UCS).
- **Búsquedas informadas:** A* Search, Greedy Best-First Search, Iterative Deepening A* (IDA\*).
- **Enfoque metaheurístico:** Algoritmo Genético (optimización de pesos de costo para heurística híbrida con aversión térmica y replanificación adaptativa).

---

## Dependencias y Requisitos

- **Python:** Versión 3.11 o superior (probado en Python 3.11, 3.12 y 3.14).
- **NumPy:** Versión 1.24 o superior (manipulación de grillas y cálculo matricial).
- **PyQt5:** Versión 5.15 o superior (interfaz gráfica de usuario y visualizador de grilla).

El resto de los módulos empleados (`heapq`, `collections`, `json`, `pathlib`, `statistics`, `argparse`, `hashlib`, etc.) forman parte de la biblioteca estándar de Python.

---

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/StackDs/Escape-Torre-IA.git
cd Escape-Torre-IA
```

2. (Opcional, recomendado) Crear y activar un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Instalar las dependencias necesarias:

```bash
pip install -r requirements.txt
```

---

## Estructura del Proyecto

```text
Escape-Torre-IA/
├── configs/                  # Archivos de configuración en formato JSON
│   ├── benchmark_final.json  # Configuración base del benchmark unificado (2.100)
│   └── experimentos/         # Configuraciones complementarias de experimentación
│       └── principal.json
├── maps/                     # Mapas discretos de 50x50 en formato de texto plano
│   ├── bottleneck.txt
│   ├── corporate_maze.txt
│   └── open_area.txt
├── report/                   # Informe formal acerca del diseño y desarrollo.
│   ├── Informe.tex
│   └── logo_udec.png
├── results/                  # Persistencia de resultados experimentales y políticas
│   ├── policies/             # Políticas entrenadas del algoritmo genético
│   └── raw/                  # Datos del benchmarking (manifiestos, runs y reportes)
│       └── gui/
├── scripts/                  # Scripts de ejecución directa
│   ├── run_gui.py
│   ├── run_benchmark.py
│   ├── train_genetic.py
├── src/                      # Código fuente modular de la aplicación
│   ├── algorithms/           # Implementación de los algoritmos de búsqueda
│   │   ├── Uninformed/
│   │   ├── Informed/
│   │   └── Genetic/
│   ├── models/               # Clases del dominio del problema (Celda, Agente, Mapa)
│   ├── simulation/           # Motor de simulación, propagación de fuego y resolución de turnos
│   ├── evaluation/           # Módulos de benchmarking masivo, métricas y reporte tabular
│   └── gui/                  # Componentes de la interfaz de usuario
├── main.py
├── requirements.txt
└── README.md
```

---

## Uso del Programa

El punto de acceso principal es `main.py`, el cual provee una interfaz unificada de línea de comandos mediante subcomandos.

### Interfaz Gráfica Interactiva (GUI)

La interfaz gráfica permite visualizar la evacuación paso a paso o en tiempo real, configurar parámetros, inspeccionar métricas y gestionar los experimentos:

```bash
# Iniciar la interfaz gráfica por defecto
python3 main.py

```

### Ejecución de Benchmarks Masivos

El subcomando `benchmark` automatiza la ejecución por lotes sobre múltiples semillas, mapas y algoritmos

Puede ser ejecutado desde la interfaz grafica del programa.

**Mecanismo de Persistencia y Reanudación:**

- Cada run individual finalizada se guarda como un archivo JSON independiente dentro de la carpeta `runs/` (`0.json`, `1.json`, etc.).
- Si el proceso se detiene voluntariamente o se interrumpe mediante `Ctrl+C`, las corridas completas se conservan intactas. Al reiniciar el comando con la misma carpeta de destino, el sistema valida la firma en `manifiesto.json` y continúa exactamente desde el caso pendiente siguiente.

### Entrenamiento del Algoritmo Genético

Para optimizar los pesos de la función de evaluación y los hiperparámetros de replanificación de la política genética:

```bash
# Entrenar una política con parámetros por defecto
python3 main.py train --config configs/benchmark_final.json --salida results/policies/nueva_politica.json

# Personalizar el tamaño de población, generaciones y semillas de entrenamiento
python3 main.py train --poblacion 12 --generaciones 8 --semillas 1000 1001 1002 1003 --salida results/policies/politica_custom.json
```

---

## Resumen Metodológico y Algoritmos

1. **Protocolo Atómico por Turno:**
   - Propagación del fuego con probabilidad $p=0.5$ cada $k=2$ turnos.
   - Replanificación simultánea sobre estado congelado.
   - Resolución de conflictos mediante cupos deterministas y sorteos con generador seudoaleatorio (PRNG) desacoplado por semilla.
   - Admisión en salida de máximo $C_E = 2$ agentes por turno.
2. **Función de Costo con Penalización por Congestión:**
   UCS, A* e IDA* evalúan el costo de arista $c(u,v) = 1 + \alpha (\text{ocupacion}(v)/\text{capacidad}(v))^2$ con $\alpha = 1.2$.
3. **Control de Validez y Zona de Exclusión:**
   Se impone una distancia mínima de exclusión de ignición a la salida ($D_{\min} \ge 10$) para evitar bloqueos tempranos inmediatos y asegurar la validez de las mediciones de evacuación.
4. **Optimización por Caché de Sufijos:**
   En pasillos y filas congestionadas, los agentes reutilizan subrutas válidas calculadas en el mismo turno en tiempo $O(1)$, reduciendo en más de un 60% las invocaciones de búsqueda sin alterar las trayectorias resultantes.

---

## Uso Académico

Este proyecto fue desarrollado en el marco académico de la carrera de Ingeniería Civil Informática de la Universidad de Concepción para el curso de Inteligencia Artificial.
