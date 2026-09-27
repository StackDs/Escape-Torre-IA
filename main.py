#!/usr/bin/env python3
"""Punto de entrada unificado para Escape de la Torre IA.

Subcomandos disponibles:
  gui        Inicia la interfaz gráfica interactiva (PyQt5)
  benchmark  Ejecuta benchmarks de búsqueda y evaluación masiva
  train      Entrena la política del algoritmo genético
  test       Ejecuta la suite de pruebas unitarias
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def _cmd_gui(args):
    from src.gui.app import MainWindow, aplicar_tema
    from PyQt5 import QtCore, QtWidgets

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication.instance()
    creado = False
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        creado = True

    aplicar_tema(app)
    ventana = MainWindow(algoritmo_inicial=args.algoritmo, mapa_inicial=args.mapa)
    ventana.show()

    if creado:
        return app.exec_()
    return 0


def _cmd_benchmark(args):
    from scripts.run_benchmark import ejecutar_bench

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


def _cmd_train(args):
    from scripts.train_genetic import ejecutar_entrenamiento

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
        print(f"Error durante el entrenamiento: {error}", file=sys.stderr, flush=True)
        return 1


def _cmd_test(args):
    from scripts.run_tests import main as run_tests_main

    return run_tests_main()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="comando", help="Subcomando a ejecutar")

    # Subcomando: gui
    parser_gui = subparsers.add_parser("gui", help="Iniciar interfaz gráfica interactiva (PyQt5)")
    parser_gui.add_argument("--algoritmo", help="Algoritmo inicial (bfs, dfs, ucs, a_star, greedy, ida_star, genetico)")
    parser_gui.add_argument("--mapa", help="Ruta al mapa inicial")
    parser_gui.set_defaults(func=_cmd_gui)

    # Subcomando: benchmark
    parser_bench = subparsers.add_parser("benchmark", help="Ejecutar benchmark de algoritmos")
    parser_bench.add_argument("--config", default=str(RAIZ / "configs/benchmark_final.json"), help="Archivo JSON de configuración")
    parser_bench.add_argument("--salida", default=str(RAIZ / "results/raw/bench_unificado"), help="Carpeta de resultados")
    parser_bench.add_argument("--iteraciones", type=int, help="Usar solo las primeras N semillas de la configuración")
    parser_bench.add_argument("--limite-ejecuciones", type=int, help="Cantidad máxima de intentos nuevos")
    parser_bench.add_argument("--solo-reporte", action="store_true", help="Regenerar reporte de texto sin simular")
    parser_bench.add_argument("--sin-genetico", action="store_true", help="Forzar exclusión del algoritmo genético")
    parser_bench.add_argument("--con-genetico", action="store_true", help="Exigir inclusión del algoritmo genético")
    parser_bench.add_argument("--politica-genetica", help="Ruta a política genética entrenada")
    parser_bench.set_defaults(func=_cmd_benchmark)

    # Subcomando: train
    parser_train = subparsers.add_parser("train", help="Entrenar la política del algoritmo genético")
    parser_train.add_argument("--config", default=str(RAIZ / "configs/benchmark_final.json"), help="Archivo JSON de configuración")
    parser_train.add_argument("--salida", default=str(RAIZ / "results/policies/mejor.json"), help="Ruta de destino para la política")
    parser_train.add_argument("--poblacion", type=int, default=10, help="Estrategias por generación")
    parser_train.add_argument("--generaciones", type=int, default=5, help="Cantidad de generaciones")
    parser_train.add_argument("--semillas", type=int, nargs="+", default=[1000, 1001, 1002], help="Semillas de entrenamiento")
    parser_train.add_argument("--semilla-genetica", type=int, default=42, help="Semilla del generador evolutivo")
    parser_train.set_defaults(func=_cmd_train)

    # Subcomando: test
    parser_test = subparsers.add_parser("test", help="Ejecutar suite de pruebas unitarias")
    parser_test.set_defaults(func=_cmd_test)

    # Si se invoca sin argumentos, mostrar ayuda o iniciar GUI
    if argv is None and len(sys.argv) == 1:
        print("Iniciando Interfaz Gráfica (usa 'python3 main.py --help' para ver subcomandos de terminal)...", flush=True)
        return _cmd_gui(argparse.Namespace(algoritmo=None, mapa=None))

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
