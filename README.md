# Escape-Torre-IA

## Simulación y benchmark

El proyecto requiere Python 3.11 o superior y NumPy. Los comandos se ejecutan desde la raíz del repositorio.

- [Motor y ejemplos de simulación](docs/motor_simulacion.md)
- [Benchmark: configuración, guardado y reanudación](docs/benchmark.md)
- [Decisiones metodológicas](docs/decisiones_metodologicas.md)
- [Modelo genético](docs/modelo_genetico.md)

```bash
# Iniciar la interfaz gráfica interactiva (PyQt5)
python3 main.py gui

# Ejecutar benchmark unificado (soporta perfiles e interrupción segura)
python3 main.py benchmark --config configs/experimentos/principal.json --salida results/raw/principal_final

# Entrenar política del algoritmo genético
python3 main.py train --config configs/benchmark_final.json --salida results/policies/mejor.json

# Ejecutar suite de pruebas unitarias
python3 main.py test
```

También es posible ejecutar los scripts directamente desde la carpeta `scripts/` (`run_gui.py`, `run_benchmark.py`, `train_genetic.py`, `run_tests.py`), o los comandos clásicos:
```bash
python3 -m unittest discover -s tests -v
python3 -m src.evaluation.benchmark --config configs/experimentos/principal.json --salida results/raw/principal_final
```

Repetir el comando del benchmark continúa desde sus corridas guardadas. Si cambian parámetros, mapas o código, usar otra carpeta de salida. La evaluación tiene una única fase final; por defecto, ambiente principal, 100 repeticiones, 150 personas, tres mapas y siete algoritmos (2.100 simulaciones). El único ambiente activo usa probabilidad de fuego 0,5 y k=2; inicia con Ejecutar selección. Consulta la [guía gráfica](docs/gui_benchmark.md).
