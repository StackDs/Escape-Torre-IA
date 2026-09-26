"""Ejecuta las seis busquedas y guarda sus resultados, sin entrenar ni usar el genetico."""

import argparse
import json
from pathlib import Path

from src.evaluation.benchmark import ejecutar_benchmark


RAIZ = Path(__file__).resolve().parent
ALGORITMOS = ["bfs", "dfs", "ucs", "a_star", "greedy", "ida_star"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(RAIZ / "configs/benchmark_final.json"))
    parser.add_argument("--salida", default=str(RAIZ / "results/raw/bench_sin_genetico_200"))
    parser.add_argument("--iteraciones", type=int,
                        help="Usar solo las primeras N semillas de la configuracion")
    parser.add_argument("--limite-ejecuciones", type=int,
                        help="Cantidad maxima de intentos nuevos en esta invocacion")
    args = parser.parse_args()

    try:
        with open(args.config, encoding="utf-8") as archivo:
            config = json.load(archivo)

        # Mantener los mismos mapas, poblaciones y fuego para todas las busquedas.
        config["algoritmos"] = ALGORITMOS.copy()
        config.pop("politica_genetica", None)
        if args.iteraciones is not None:
            if not 1 <= args.iteraciones <= len(config["semillas"]):
                raise ValueError("Las iteraciones deben estar entre 1 y la cantidad de semillas del JSON.")
            config["semillas"] = config["semillas"][:args.iteraciones]
            if len(config["semillas"]) < 80:
                config["modo"] = "piloto"

        total = len(config["mapas"]) * len(config["poblaciones"]) * len(config["semillas"]) * len(ALGORITMOS)
        reporte = Path(args.salida).resolve() / "reporte_benchmark.txt"
        print("BENCHMARK SIN GENETICO", flush=True)
        print("Algoritmos: BFS, DFS, UCS, A*, Greedy e IDA*", flush=True)
        print("Agentes por simulacion: " + ", ".join(str(n) for n in config["poblaciones"]), flush=True)
        print(f"Iteraciones por mapa, poblacion y algoritmo: {len(config['semillas'])}", flush=True)
        print(f"Modo: {config['modo']} | Corridas previstas: {total}", flush=True)
        print("Reporte: " + str(reporte), flush=True)
        print("Ctrl+C conserva las corridas completas. Repite el mismo comando para continuar.", flush=True)

        progreso = ejecutar_benchmark(config, args.salida, args.limite_ejecuciones)
        print(json.dumps(progreso, ensure_ascii=False), flush=True)
        print("Reporte guardado: " + str(reporte), flush=True)
        return 1 if progreso["errores_esta_invocacion"] else 0
    except KeyboardInterrupt:
        print("Interrumpido. Repite el mismo comando para continuar.", flush=True)
        return 130
    except (ValueError, OSError, TypeError, KeyError) as error:
        print("No se pudo completar el benchmark: " + str(error), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
