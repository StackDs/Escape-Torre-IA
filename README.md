# Escape-Torre-IA

## Simulación y benchmark

El proyecto requiere Python 3.11 o superior y NumPy. Los comandos se ejecutan desde la raíz del repositorio.

- [Motor y ejemplos de simulación](docs/motor_simulacion.md)
- [Benchmark: configuración, guardado y reanudación](docs/benchmark.md)
- [Resultados de calibración piloto](docs/calibracion_piloto.md)
- [Decisiones metodológicas](docs/decisiones_metodologicas.md)
- [Modelo genético](docs/modelo_genetico.md)

```bash
python3 -m unittest discover -s tests -v
python3 -m src.evaluation.benchmark --config configs/piloto_inicial.json --salida results/raw/piloto_inicial
```

Repetir el comando del benchmark continúa desde sus corridas guardadas. Si cambian parámetros, mapas o código, usar otra carpeta de salida. Los pilotos no sustituyen el benchmark final ni el entrenamiento genético.
