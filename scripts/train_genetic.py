#!/usr/bin/env python3
"""Script de entrenamiento para la política genética.

Permite optimizar los pesos de congestión, riesgo y umbral de bloqueo
utilizando los escenarios definidos en la configuración.
"""

import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.evaluation.train_genetic import entrenar
from src.simulation.motor import simular


def ejecutar_entrenamiento(
    config_path=None,
    salida_path=None,
    poblacion=10,
    generaciones=5,
    semillas=None,
    semilla_genetica=42,
    callback_progreso=None,
):
    if config_path is None:
        config_path = RAIZ / "configs/benchmark_final.json"
    else:
        config_path = Path(config_path).resolve()

    if salida_path is None:
        salida_path = RAIZ / "results/policies/mejor.json"
    else:
        salida_path = Path(salida_path).resolve()

    if semillas is None:
        semillas = [1000, 1001, 1002]

    if poblacion < 3:
        raise ValueError("La población debe ser de al menos 3 individuos (tamaño de torneo evolutivo).")

    with open(config_path, encoding="utf-8") as archivo:
        config = json.load(archivo)

    semillas_eval = set(config.get("semillas", []))
    solapadas = set(semillas) & semillas_eval
    if solapadas:
        raise ValueError(
            f"Las semillas de entrenamiento {sorted(solapadas)} se solapan con las semillas de evaluación "
            "reservadas del benchmark. Debes usar semillas distintas."
        )

    escenarios = []
    for mapa in config["mapas"]:
        for poblacion_escenario in config["poblaciones"]:
            escenario = config["parametros"].copy()
            escenario["mapa"] = str((RAIZ / mapa).resolve())
            escenario["poblacion_inicial"] = poblacion_escenario
            escenarios.append(escenario)

    maximo = poblacion * generaciones * len(escenarios) * len(semillas)
    completadas = 0
    inicio = time.perf_counter()

    def simular_con_progreso(politica, escenario, semilla):
        nonlocal completadas
        resultado = simular(politica, escenario, semilla)
        completadas += 1
        minutos = (time.perf_counter() - inicio) / 60
        mensaje = (
            f"Simulaciones ejecutadas: {completadas} (máximo {maximo}) | "
            f"Transcurrido: {minutos:.1f} min"
        )
        print(mensaje, flush=True)
        if callback_progreso:
            callback_progreso(completadas, maximo, mensaje)
        return resultado

    print("INICIO DEL ENTRENAMIENTO", flush=True)
    print("Configuración: " + str(config_path), flush=True)
    print("Destino: " + str(salida_path), flush=True)
    print(f"Población: {poblacion} | Generaciones: {generaciones} | Semilla: {semilla_genetica}", flush=True)
    print("Las estrategias repetidas reutilizan su evaluación.", flush=True)

    resultado = entrenar(
        simular_con_progreso,
        escenarios,
        semillas,
        config["semillas"],
        str(salida_path),
        configuracion={
            "tamano_poblacion": poblacion,
            "generaciones": generaciones,
            "semilla": semilla_genetica,
        },
    )
    if resultado is None:
        raise ValueError("El entrenamiento rechazó la configuración o las semillas.")

    mejor, historial = resultado
    print("ENTRENAMIENTO COMPLETADO", flush=True)
    print("Parámetros:", mejor.parametros(), flush=True)
    print("Aptitud de entrenamiento:", mejor.aptitud, flush=True)
    print("Simulaciones realizadas:", completadas, flush=True)
    print("Archivo guardado:", salida_path, flush=True)
    return mejor, historial


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(RAIZ / "configs/benchmark_final.json"),
        help="Archivo JSON de configuración",
    )
    parser.add_argument(
        "--salida",
        default=str(RAIZ / "results/policies/mejor.json"),
        help="Ruta de destino para la política entrenada",
    )
    parser.add_argument(
        "--poblacion",
        type=int,
        default=10,
        help="Cantidad de estrategias de búsqueda por generación",
    )
    parser.add_argument(
        "--generaciones",
        type=int,
        default=5,
        help="Cantidad de generaciones a evolucionar",
    )
    parser.add_argument(
        "--semillas",
        type=int,
        nargs="+",
        default=[1000, 1001, 1002],
        help="Semillas de entrenamiento",
    )
    parser.add_argument(
        "--semilla-genetica",
        type=int,
        default=42,
        help="Semilla del algoritmo genético",
    )
    args = parser.parse_args(argv)

    try:
        ejecutar_entrenamiento(
            config_path=args.config,
            salida_path=args.salida,
            poblacion=args.poblacion,
            generaciones=args.generaciones,
            semillas=args.semillas,
            semilla_genetica=args.semilla_genetica,
        )
        return 0
    except Exception as error:
        print("Error durante el entrenamiento: " + str(error), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
