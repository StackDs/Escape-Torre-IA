#!/usr/bin/env python3
"""Script unificado de ejecución de benchmarks.

Permite ejecutar benchmarks finales (y reanudar configuraciones históricas) de los algoritmos de búsqueda,
con soporte automático para incluir o excluir el algoritmo genético según esté
entrenado o según los parámetros especificados.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.evaluation.benchmark import ejecutar_benchmark, regenerar_reporte


def ejecutar_bench(
    config_path=None,
    salida_path=None,
    iteraciones=None,
    limite_ejecuciones=None,
    solo_reporte=False,
    sin_genetico=False,
    con_genetico=False,
    politica_genetica=None,
):
    if salida_path is None:
        salida_path = RAIZ / "results/raw/benchmark_ejecucion"
    else:
        salida_path = Path(salida_path).resolve()

    if solo_reporte:
        reporte = regenerar_reporte(salida_path)
        print("Reporte regenerado: " + str(reporte), flush=True)
        return {"reporte": str(reporte)}

    if config_path is None:
        config_path = RAIZ / "configs/benchmark_final.json"
    else:
        config_path = Path(config_path).resolve()

    with open(config_path, encoding="utf-8") as archivo:
        config = json.load(archivo)

    # Determinar manejo de política genética
    politica_ruta = None
    if politica_genetica:
        politica_ruta = Path(politica_genetica).resolve()
    elif "politica_genetica" in config:
        politica_ruta = (RAIZ / config["politica_genetica"]).resolve()
    else:
        politica_ruta = RAIZ / "results/policies/mejor.json"

    tiene_politica = politica_ruta.is_file()

    if sin_genetico:
        config["algoritmos"] = [a for a in config["algoritmos"] if a != "genetico"]
        config.pop("politica_genetica", None)
    elif con_genetico or "genetico" in config.get("algoritmos", []) or (politica_genetica and tiene_politica):
        if (con_genetico or (politica_genetica and tiene_politica)) and "genetico" not in config["algoritmos"]:
            config["algoritmos"].append("genetico")
        if tiene_politica:
            config["politica_genetica"] = str(politica_ruta)
        elif con_genetico:
            raise ValueError(
                f"Se solicitó --con-genetico pero no se encontró la política entrenada en: {politica_ruta}\n"
                "Entrena primero la política con 'main.py train' o ejecuta sin genético con '--sin-genetico'."
            )
        else:
            print(
                f"[AVISO] La política genética no se encontró en '{politica_ruta}'.\n"
                "Ejecutando benchmark para el resto de los algoritmos sin genético.",
                flush=True,
            )
            config["algoritmos"] = [a for a in config["algoritmos"] if a != "genetico"]
            config.pop("politica_genetica", None)

    if iteraciones is not None:
        if not 1 <= iteraciones <= len(config["semillas"]):
            raise ValueError("Las iteraciones deben estar entre 1 y la cantidad de semillas del JSON.")
        config["semillas"] = config["semillas"][:iteraciones]
        if config["modo"] == "final" and len(config["semillas"]) < 80:
            raise ValueError("La evaluación final requiere al menos 80 repeticiones; no se convierte en otra fase.")

    total = (
        len(config["mapas"])
        * len(config["poblaciones"])
        * len(config["semillas"])
        * len(config["algoritmos"])
    )
    reporte_archivo = salida_path / "reporte_benchmark.txt"

    print("=" * 60, flush=True)
    print("EJECUCIÓN DE BENCHMARK", flush=True)
    print("=" * 60, flush=True)
    print("Algoritmos: " + ", ".join(config["algoritmos"]), flush=True)
    print("Mapas: " + ", ".join(Path(m).name for m in config["mapas"]), flush=True)
    print("Poblaciones: " + ", ".join(str(n) for n in config["poblaciones"]), flush=True)
    print(f"Semillas por configuración: {len(config['semillas'])}", flush=True)
    print(f"Modo: {config['modo']} | Corridas totales previstas: {total}", flush=True)
    print("Carpeta de salida: " + str(salida_path), flush=True)
    print("Ctrl+C conserva las corridas completas.", flush=True)
    print("=" * 60, flush=True)

    progreso = ejecutar_benchmark(config, str(salida_path), limite_ejecuciones)
    print("\nRESUMEN DE BENCHMARK:", flush=True)
    print(json.dumps(progreso, ensure_ascii=False, indent=2), flush=True)
    print("Reporte final guardado en: " + str(reporte_archivo), flush=True)
    return progreso


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(RAIZ / "configs/benchmark_final.json"),
        help="Archivo JSON de configuración del benchmark",
    )
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "results/raw/bench_unificado"),
        help="Carpeta donde se guardarán resultados y reporte",
    )
    parser.add_argument(
        "--iteraciones",
        type=int,
        help="Usar solo las primeras N semillas de la configuración",
    )
    parser.add_argument(
        "--limite-ejecuciones",
        type=int,
        help="Cantidad máxima de intentos nuevos en esta invocación",
    )
    parser.add_argument(
        "--solo-reporte",
        action="store_true",
        help="Regenerar reporte de texto a partir de resultados previos sin ejecutar simulaciones",
    )
    parser.add_argument(
        "--sin-genetico",
        action="store_true",
        help="Forzar exclusión del algoritmo genético aunque esté en la configuración",
    )
    parser.add_argument(
        "--con-genetico",
        action="store_true",
        help="Exigir inclusión del algoritmo genético (falla si la política no está entrenada)",
    )
    parser.add_argument(
        "--politica-genetica",
        help="Ruta personalizada al archivo JSON de política genética entrenada",
    )
    args = parser.parse_args(argv)

    try:
        progreso = ejecutar_bench(
            config_path=args.config,
            salida_path=args.salida,
            iteraciones=args.iteraciones,
            limite_ejecuciones=args.limite_ejecuciones,
            solo_reporte=args.solo_reporte,
            sin_genetico=args.sin_genetico,
            con_genetico=args.con_genetico,
            politica_genetica=args.politica_genetica,
        )
        if args.solo_reporte:
            return 0
        return 1 if progreso.get("errores_esta_invocacion", 0) > 0 else 0
    except KeyboardInterrupt:
        print("\nBenchmark interrumpido por el usuario.", flush=True)
        return 130
    except Exception as error:
        print(f"Error en benchmark: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
