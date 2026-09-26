import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.algorithms.Genetic.individuo import Individuo
from src.algorithms.Genetic.politica import PoliticaGenetica, calcular_riesgos, manhattan
from src.evaluation.train_genetic import entrenar
from src.models.celda import Celda


def crear_mapa():
    mapa = np.empty((6, 7), dtype=object)
    for fila in range(6):
        for columna in range(7):
            mapa[fila, columna] = Celda('E' if (fila, columna) == (5, 6) else '.', 4)
    return mapa


class PruebasOptimizacionGenetica(unittest.TestCase):
    def test_distancias_identicas_al_minimo_manhattan(self):
        azar = random.Random(7)
        for filas, columnas in [(1, 1), (1, 10), (10, 1), (6, 7)]:
            posiciones = [(f, c) for f in range(filas) for c in range(columnas)]
            for _ in range(10):
                fuego = azar.sample(posiciones, azar.randint(1, len(posiciones)))
                riesgos = calcular_riesgos(filas, columnas, fuego)
                for posicion in posiciones:
                    esperado = 1 / (1 + min(manhattan(posicion, foco) for foco in fuego))
                    self.assertEqual(riesgos[posicion], esperado)
        self.assertEqual(calcular_riesgos(3, 4, []), {})

    def test_cache_se_comparte_y_se_invalida_al_cambiar_fuego(self):
        mapa = crear_mapa()
        mapa[0, 6].quemar()
        politica = PoliticaGenetica(Individuo(2, 5, 3))
        with patch('src.algorithms.Genetic.politica.calcular_riesgos', wraps=calcular_riesgos) as calcular:
            self.assertIsNotNone(politica.planificar(mapa, (0, 0)))
            self.assertIsNotNone(politica.planificar(mapa, (1, 0)))
            self.assertEqual(calcular.call_count, 1)
            mapa[1, 6].quemar()
            politica.planificar(mapa, (1, 0))
            self.assertEqual(calcular.call_count, 2)
        esperado = 1 / (1 + min(manhattan((1, 5), foco) for foco in [(0, 6), (1, 6)]))
        self.assertEqual(politica._riesgos[(1, 5)], esperado)

    def test_riesgo_ignora_muros_y_ocupacion_sigue_actualizandose(self):
        mapa = crear_mapa()
        mapa[0, 6].quemar()
        mapa[0, 5].simbolo = '#'
        politica = PoliticaGenetica(Individuo(10, 5, 3))
        politica.planificar(mapa, (0, 0))
        self.assertEqual(politica._riesgos[(0, 4)], 1 / 3)
        cache = politica._riesgos
        mapa[1, 0].agentes = [object()] * 4
        ruta = politica.planificar(mapa, (0, 0))
        referencia = PoliticaGenetica(Individuo(10, 5, 3)).planificar(mapa, (0, 0))
        self.assertEqual(ruta, referencia)
        self.assertIs(cache, politica._riesgos)

    def test_misma_forma_con_otro_fuego_no_reutiliza_datos_obsoletos(self):
        politica = PoliticaGenetica(Individuo(1, 1, 3))
        primero = crear_mapa()
        primero[0, 6].quemar()
        politica.planificar(primero, (0, 0))
        segundo = crear_mapa()
        segundo[5, 0].quemar()
        ruta = politica.planificar(segundo, (0, 0))
        esperado = PoliticaGenetica(Individuo(1, 1, 3)).planificar(segundo, (0, 0))
        self.assertEqual(ruta, esperado)
        self.assertEqual(politica._riesgos[(4, 0)], 0.5)

    def test_peso_cero_no_calcula_riesgo(self):
        mapa = crear_mapa()
        mapa[0, 6].quemar()
        with patch('src.algorithms.Genetic.politica.calcular_riesgos') as calcular:
            self.assertIsNotNone(PoliticaGenetica(Individuo(1, 0, 3)).planificar(mapa, (0, 0)))
            calcular.assert_not_called()

    def test_cache_de_aptitud_conserva_historial_y_ahorra_simulaciones(self):
        opciones = {'tamano_poblacion': 4, 'generaciones': 4, 'semilla': 9,
                    'probabilidad_cruce': 0, 'probabilidad_mutacion': 0}
        escenarios = [{'poblacion_inicial': 10}]
        llamadas = []
        def simular(politica, escenario, semilla):
            llamadas.append(politica.individuo.parametros())
            evacuados = int(politica.individuo.peso_congestion)
            return {'evacuados': evacuados, 'fallecidos': 10 - evacuados, 'pendientes': 0}
        with tempfile.TemporaryDirectory() as carpeta:
            sin_cache = entrenar(simular, escenarios, [1, 2], [100], Path(carpeta)/'base.json',
                                  opciones, reutilizar_evaluaciones=False)
            cantidad_base = len(llamadas)
            llamadas.clear()
            con_cache = entrenar(simular, escenarios, [1, 2], [100], Path(carpeta)/'cache.json', opciones)
            self.assertLess(len(llamadas), cantidad_base)
            self.assertEqual(sin_cache[0].parametros(), con_cache[0].parametros())
            self.assertEqual(sin_cache[1], con_cache[1])
            registro = json.loads((Path(carpeta)/'cache.json').read_text())
            self.assertEqual(registro['evaluaciones_individuos']['solicitadas'], 16)
            self.assertEqual(registro['evaluaciones_individuos']['simuladas'], 4)
            self.assertEqual(registro['evaluaciones_individuos']['reutilizadas'], 12)


if __name__ == '__main__':
    unittest.main()
