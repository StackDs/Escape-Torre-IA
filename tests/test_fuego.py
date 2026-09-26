import math
import random
import unittest

import numpy as np

from src.models.celda import Celda
from src.models.agente import Agente, State
from src.simulation.fuego import seleccionar_focos, encender_focos, propagar_fuego


def crear_mapa(filas):
    mapa = np.empty((len(filas), len(filas[0])), dtype=object)
    for fila, texto in enumerate(filas):
        for columna, simbolo in enumerate(texto):
            mapa[fila, columna] = Celda(simbolo, 0 if simbolo == "#" else 4)
    return mapa


class SorteoControlado:
    def __init__(self, valores):
        self.valores = iter(valores)
        self.llamadas = 0

    def random(self):
        self.llamadas += 1
        return next(self.valores)


class PruebasFuego(unittest.TestCase):
    def test_focos_reproducibles_sin_ocupantes_muros_ni_salida(self):
        mapa = crear_mapa(["#..E", "...."])
        mapa[0, 1].agentes.append(Agente(0, 0, 1))
        focos = seleccionar_focos(mapa, 4, 42)
        self.assertEqual(focos, seleccionar_focos(mapa, 4, 42))
        self.assertEqual(len(set(focos)), 4)
        for posicion in focos:
            self.assertEqual(mapa[posicion].simbolo, ".")
            self.assertFalse(mapa[posicion].agentes)
            self.assertFalse(mapa[posicion].quemada)
        self.assertIsNone(seleccionar_focos(mapa, 6))
        self.assertEqual(seleccionar_focos(mapa, 0), [])

    def test_focos_invalidos_no_modifican_parcialmente_el_mapa(self):
        for focos in [[(0, 0), (0, 2)], [(0, 0), (0, 0)], [(0, 0), (2, 0)]]:
            mapa = crear_mapa(["..E"])
            self.assertIsNone(encender_focos(mapa, focos))
            self.assertFalse(mapa[0, 0].quemada)
        mapa = crear_mapa(["..E"])
        self.assertEqual(encender_focos(mapa, [(0, 1)]), [(0, 1)])
        self.assertTrue(mapa[0, 1].quemada)

    def test_frecuencia_y_ausencia_de_cascada(self):
        mapa = crear_mapa(["....E"])
        encender_focos(mapa, [(0, 0)])
        azar = random.Random(5)
        estado_azar = azar.getstate()
        for turno in [0, 1, 2]:
            self.assertEqual(propagar_fuego(mapa, turno, 3, 1, azar), [])
        self.assertEqual(azar.getstate(), estado_azar)
        self.assertEqual(propagar_fuego(mapa, 3, 3, 1, azar), [(0, 1)])
        self.assertFalse(mapa[0, 2].quemada)
        self.assertEqual(propagar_fuego(mapa, 6, 3, 1, azar), [(0, 2)])
        self.assertTrue(mapa[0, 0].quemada)

    def test_muros_y_diagonales(self):
        mapa = crear_mapa(["...", ".#.", "..E"])
        encender_focos(mapa, [(0, 0)])
        self.assertEqual(propagar_fuego(mapa, 1, 1, 1, random.Random(0)), [(0, 1), (1, 0)])
        self.assertFalse(mapa[1, 1].quemada)
        aislado = crear_mapa([".#E"])
        encender_focos(aislado, [(0, 0)])
        self.assertEqual(propagar_fuego(aislado, 1, 1, 1, random.Random(0)), [])
        self.assertFalse(aislado[0, 2].quemada)

    def test_un_intento_por_celda_y_reintento_posterior(self):
        mapa = crear_mapa(["..."])
        encender_focos(mapa, [(0, 0), (0, 2)])
        azar = SorteoControlado([0.8, 0.2])
        self.assertEqual(propagar_fuego(mapa, 1, 1, 0.4, azar), [])
        self.assertEqual(azar.llamadas, 1)
        self.assertEqual(propagar_fuego(mapa, 2, 1, 0.4, azar), [(0, 1)])
        self.assertEqual(azar.llamadas, 2)

    def test_fuego_alcanza_salida_y_agentes_sin_registrar_bajas(self):
        mapa = crear_mapa(["..E"])
        agente = Agente(0, 0, 1)
        mapa[0, 1].agentes.append(agente)
        encender_focos(mapa, [(0, 0)])
        azar = random.Random(0)
        propagar_fuego(mapa, 1, 1, 1, azar)
        self.assertTrue(mapa[0, 1].quemada)
        self.assertEqual(agente.estado, State.ACTIVO)
        self.assertEqual(mapa[0, 1].agentes, [agente])
        self.assertEqual(propagar_fuego(mapa, 2, 1, 1, azar), [(0, 2)])

    def test_probabilidad_cero_y_sin_focos(self):
        mapa = crear_mapa(["..E"])
        azar = random.Random(0)
        self.assertEqual(propagar_fuego(mapa, 1, 1, 1, azar), [])
        encender_focos(mapa, [(0, 0)])
        self.assertEqual(propagar_fuego(mapa, 2, 1, 0, azar), [])
        self.assertFalse(mapa[0, 1].quemada)

    def test_mismo_incendio_con_distinta_ocupacion(self):
        mapas = [crear_mapa(["....", "...E"]) for _ in range(2)]
        generadores = [random.Random(42), random.Random(42)]
        for mapa in mapas:
            encender_focos(mapa, [(0, 0)])
        mapas[1][0, 1].agentes.append(Agente(0, 0, 1))
        for turno in range(1, 15):
            primero = propagar_fuego(mapas[0], turno, 2, 0.4, generadores[0])
            segundo = propagar_fuego(mapas[1], turno, 2, 0.4, generadores[1])
            self.assertEqual(primero, segundo)

    def test_parametros_invalidos(self):
        mapa = crear_mapa([".E"])
        for turno, k, probabilidad in [(-1, 1, 0.4), (1, 0, 0.4),
                                      (1, 1, -0.1), (1, 1, 1.1),
                                      (1, 1, math.nan), (1, 1, math.inf)]:
            self.assertIsNone(propagar_fuego(mapa, turno, k, probabilidad, random.Random(0)))


if __name__ == "__main__":
    unittest.main()
