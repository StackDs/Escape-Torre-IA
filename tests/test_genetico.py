import heapq
import json
import math
import random
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.models.celda import Celda
from src.models.agente import Agente, State
from src.algorithms.Informed.A_Star import a_star
from src.algorithms.Genetic.individuo import Individuo
from src.algorithms.Genetic.politica import PoliticaGenetica
from src.algorithms.Genetic.genetico import (
    LIMITES_INICIALES, evolucionar, mutar, cruzar
)
from src.evaluation.train_genetic import entrenar, evaluar_individuo


def crear_mapa(filas):
    mapa = np.empty((len(filas), len(filas[0])), dtype=object)
    for f, texto in enumerate(filas):
        for c, simbolo in enumerate(texto):
            mapa[f, c] = Celda(simbolo, 0 if simbolo == '#' else 4)
    return mapa


class PruebasGenetico(unittest.TestCase):
    def test_individuo_valida_y_copia(self):
        for valores in [(-1, 1, 2), (1, math.inf, 2), (1, 1, 0), (1, 1, 1.5)]:
            with self.assertRaises(ValueError):
                Individuo(*valores)
        original = Individuo(2, 5, 3)
        original.aptitud = 0.5
        copia = original.copiar()
        copia.peso_riesgo = 8
        self.assertEqual(original.peso_riesgo, 5)
        self.assertEqual(copia.aptitud, 0.5)

    def test_sin_riesgo_coincide_con_astar(self):
        mapa = crear_mapa(['....E', '.....'])
        mapa[0, 2].agentes = [object()] * 4
        politica = PoliticaGenetica(Individuo(10, 0, 3))
        self.assertEqual(politica.planificar(mapa, (0, 0)), a_star(mapa, (0, 0), 10))
        self.assertNotIn((0, 2), politica.planificar(mapa, (0, 0)))
        self.assertEqual(len(mapa[0, 2].agentes), 4)

    def test_riesgo_cambia_ruta_sin_modificar_mapa(self):
        mapa = crear_mapa(['##.##', '.....', '.###E', '.....', '.....'])
        mapa[0, 2].quemar()
        base = PoliticaGenetica(Individuo(0, 0, 3)).planificar(mapa, (2, 0))
        segura = PoliticaGenetica(Individuo(0, 10, 3)).planificar(mapa, (2, 0))
        self.assertEqual(base[0], (1, 0))
        self.assertEqual(segura[0], (3, 0))
        self.assertEqual(segura[-1], (2, 4))
        self.assertTrue(mapa[0, 2].quemada)

    def test_politica_coincide_con_costo_optimo_de_referencia(self):
        mapa = crear_mapa(['.....', '.#.#.', '....E', '.....'])
        mapa[3, 2].quemar()
        mapa[0, 1].agentes = [object()] * 4
        individuo = Individuo(3, 4, 2)
        ruta = PoliticaGenetica(individuo).planificar(mapa, (0, 0))
        def costo(posicion):
            distancia = abs(posicion[0] - 3) + abs(posicion[1] - 2)
            return 1 + 3 * (len(mapa[posicion].agentes) / 4) ** 2 + 4 / (1 + distancia)
        # Dijkstra de referencia independiente de la heuristica.
        cola = [(0, (0, 0))]
        distancias = {(0, 0): 0}
        while cola:
            g, pos = heapq.heappop(cola)
            if g != distancias[pos]:
                continue
            for df, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                v = (pos[0] + df, pos[1] + dc)
                if not (0 <= v[0] < 4 and 0 <= v[1] < 5):
                    continue
                if mapa[v].simbolo == '#' or mapa[v].quemada:
                    continue
                nuevo = g + costo(v)
                if nuevo < distancias.get(v, math.inf):
                    distancias[v] = nuevo
                    heapq.heappush(cola, (nuevo, v))
        self.assertAlmostEqual(sum(costo(p) for p in ruta), distancias[(2, 4)])

    def test_casos_limite_de_planificacion(self):
        politica = PoliticaGenetica(Individuo(2, 5, 3))
        self.assertEqual(politica.planificar(crear_mapa(['E']), (0, 0)), [])
        for filas, inicio in [(['.#E'], (0, 0)), (['..'], (0, 0)),
                              (['.EE'], (0, 0)), (['.E'], (-1, 0))]:
            self.assertIsNone(politica.planificar(crear_mapa(filas), inicio))
        mapa = crear_mapa(['.E'])
        mapa[0, 1].quemar()
        self.assertIsNone(politica.planificar(mapa, (0, 0)))

    def test_replanificacion_y_estado_esperando(self):
        mapa = crear_mapa(['...E'])
        agente = Agente(0, 0, 0)
        politica = PoliticaGenetica(Individuo(2, 5, 3))
        self.assertTrue(politica.necesita_replanificar(mapa, agente))
        agente.asignar_ruta([(0, 1), (0, 2), (0, 3)])
        agente.estado = State.ESPERANDO
        agente.turnos_bloqueado = 2
        self.assertFalse(politica.necesita_replanificar(mapa, agente))
        agente.turnos_bloqueado = 3
        self.assertTrue(politica.necesita_replanificar(mapa, agente))
        agente.turnos_bloqueado = 0
        mapa[0, 2].quemar()
        self.assertTrue(politica.necesita_replanificar(mapa, agente))
        agente.estado = State.MUERTO
        self.assertFalse(politica.necesita_replanificar(mapa, agente))

    def test_operadores_no_modifican_padres_y_respetan_limites(self):
        azar = random.Random(9)
        padre = Individuo(2, 5, 3)
        otro = Individuo(8, 1, 7)
        hijo = cruzar(padre, otro, azar)
        self.assertIn(hijo.peso_congestion, [2, 8])
        self.assertIn(hijo.peso_riesgo, [5, 1])
        for _ in range(100):
            hijo = mutar(hijo, azar, LIMITES_INICIALES, 1, 2)
            self.assertTrue(0 <= hijo.peso_congestion <= 10)
            self.assertTrue(0 <= hijo.peso_riesgo <= 10)
            self.assertTrue(1 <= hijo.umbral_bloqueo <= 10)
            self.assertIsInstance(hijo.umbral_bloqueo, int)
            self.assertIsNone(hijo.aptitud)
        self.assertEqual(padre.parametros(), Individuo(2, 5, 3).parametros())

    def test_evolucion_reproducible_y_elitismo(self):
        def evaluar(individuo):
            return individuo.peso_congestion / 10
        mejor, historial = evolucionar(evaluar, tamano_poblacion=8, generaciones=5, semilla=42)
        segundo, repetido = evolucionar(evaluar, tamano_poblacion=8, generaciones=5, semilla=42)
        self.assertEqual(mejor.parametros(), segundo.parametros())
        self.assertEqual(historial, repetido)
        aptitudes = [fila['mejor_aptitud'] for fila in historial]
        self.assertEqual(aptitudes, sorted(aptitudes))
        self.assertEqual(mejor.aptitud, aptitudes[-1])

    def test_evaluacion_promedia_tasas_y_aisla_escenarios(self):
        escenarios = [{'poblacion_inicial': 10}, {'poblacion_inicial': 100}]
        llamadas = []
        def simular(politica, escenario, semilla):
            llamadas.append((escenario['poblacion_inicial'], semilla))
            total = escenario['poblacion_inicial']
            escenario['poblacion_inicial'] = 0
            evacuados = 5 if total == 10 else 100
            return {'evacuados': evacuados, 'fallecidos': 0, 'pendientes': total - evacuados}
        aptitud = evaluar_individuo(Individuo(1, 1, 2), simular, escenarios, [1, 2])
        self.assertEqual(aptitud, 0.75)
        self.assertEqual(llamadas, [(10, 1), (10, 2), (100, 1), (100, 2)])
        self.assertEqual(escenarios[0]['poblacion_inicial'], 10)

    def test_entrenamiento_reserva_semillas_y_guarda_json(self):
        llamadas = []
        def simular(politica, escenario, semilla):
            llamadas.append(semilla)
            return {'evacuados': 8, 'fallecidos': 1, 'pendientes': 1}
        with tempfile.TemporaryDirectory() as directorio:
            salida = Path(directorio) / 'politica.json'
            mejor, historial = entrenar(
                simular, [{'poblacion_inicial': 10}], [1, 2], [50, 51], salida,
                {'tamano_poblacion': 4, 'generaciones': 2}
            )
            registro = json.loads(salida.read_text())
            self.assertEqual(mejor.aptitud, 0.8)
            self.assertEqual(len(llamadas), 16)
            self.assertEqual(set(llamadas), {1, 2})
            self.assertEqual(registro['semillas_evaluacion_reservadas'], [50, 51])
            self.assertEqual(registro['historial'], historial)
            with self.assertRaises(ValueError):
                entrenar(simular, [{'poblacion_inicial': 10}], [1], [1], salida)

    def test_rechaza_aptitud_y_resultados_invalidos(self):
        with self.assertRaises(ValueError):
            evolucionar(lambda individuo: math.nan)
        with self.assertRaises(ValueError):
            evaluar_individuo(
                Individuo(1, 1, 2), lambda *args: {'evacuados': 11, 'fallecidos': 0, 'pendientes': 0},
                [{'poblacion_inicial': 10}], [1]
            )


if __name__ == '__main__':
    unittest.main()
