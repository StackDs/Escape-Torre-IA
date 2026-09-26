"""Entrena la politica genetica. Ejecutar: python3 -u entrenar.py"""

import argparse
import json
import time
from pathlib import Path

from src.evaluation.train_genetic import entrenar
from src.simulation.motor import simular


RAIZ = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(RAIZ / 'configs/benchmark_final.json'))
    parser.add_argument('--salida', default=str(RAIZ / 'results/policies/mejor.json'))
    parser.add_argument('--poblacion', type=int, default=10, help='Cantidad de estrategias, no personas')
    parser.add_argument('--generaciones', type=int, default=5)
    parser.add_argument('--semillas', type=int, nargs='+', default=[1000, 1001, 1002])
    parser.add_argument('--semilla-genetica', type=int, default=42)
    args = parser.parse_args()

    with open(args.config, encoding='utf-8') as archivo:
        config = json.load(archivo)
    escenarios = []
    for mapa in config['mapas']:
        for poblacion in config['poblaciones']:
            escenario = config['parametros'].copy()
            escenario['mapa'] = str((RAIZ / mapa).resolve())
            escenario['poblacion_inicial'] = poblacion
            escenarios.append(escenario)

    maximo = args.poblacion * args.generaciones * len(escenarios) * len(args.semillas)
    completadas = 0
    inicio = time.perf_counter()

    def simular_con_progreso(politica, escenario, semilla):
        nonlocal completadas
        resultado = simular(politica, escenario, semilla)
        completadas += 1
        minutos = (time.perf_counter() - inicio) / 60
        print(f'Simulaciones ejecutadas: {completadas} (máximo {maximo}) | '
              f'Transcurrido: {minutos:.1f} min', flush=True)
        return resultado

    print('INICIO DEL ENTRENAMIENTO', flush=True)
    print('Las estrategias repetidas reutilizan su evaluación; pueden ejecutarse menos simulaciones.', flush=True)
    print('La política se guarda al terminar. Este entrenamiento aún no tiene reanudación.', flush=True)
    resultado = entrenar(
        simular_con_progreso, escenarios, args.semillas, config['semillas'], args.salida,
        configuracion={'tamano_poblacion': args.poblacion, 'generaciones': args.generaciones,
                       'semilla': args.semilla_genetica}
    )
    if resultado is None:
        raise ValueError('El entrenamiento rechazó la configuración o las semillas.')
    mejor, historial = resultado
    print('ENTRENAMIENTO COMPLETADO', flush=True)
    print('Parámetros:', mejor.parametros(), flush=True)
    print('Aptitud de entrenamiento:', mejor.aptitud, flush=True)
    print('Simulaciones realizadas:', completadas, flush=True)
    print('Archivo guardado:', Path(args.salida).resolve(), flush=True)


if __name__ == '__main__':
    main()
