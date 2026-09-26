import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.models.celda import Celda
from src.simulation.motor import MotorSimulacion
from src.simulation.politicas import BUSQUEDAS, PoliticaBusqueda, ruta_valida


def crear_mapa(lineas):
    return np.array([[Celda(c, 0 if c == "#" else 2 if c == "E" else 4)
                      for c in linea] for linea in lineas], dtype=object)


def costo(mapa, ruta, alpha):
    if ruta is None:
        return None
    return sum(1 + alpha * (len(mapa[p].agentes) / mapa[p].capacidad) ** 2 for p in ruta)


class PoliticaSinCache(PoliticaBusqueda):
    """La interfaz externa conserva la validacion y una busqueda por persona."""


class TestBusquedas(unittest.TestCase):
    def test_contratos_y_no_mutacion(self):
        for nombre, buscar in BUSQUEDAS.items():
            with self.subTest(algoritmo=nombre):
                mapa = crear_mapa(["...E", ".##.", "...."])
                ruta = buscar(mapa, (2, 0))
                self.assertTrue(ruta_valida(mapa, (2, 0), ruta))
                self.assertEqual(buscar(mapa, (0, 3)), [])
                self.assertIsNone(buscar(mapa, (-1, 0)))
                self.assertIsNone(buscar(mapa, (1, 1)))
                self.assertTrue(all(not c.quemada and not c.agentes for c in mapa.flat))
                mapa[0, 3].capacidad = 0
                self.assertIsNone(buscar(mapa, (2, 0)))
                mapa[0, 3].capacidad = 2
                mapa[0, 3].quemada = True
                self.assertIsNone(buscar(mapa, (2, 0)))

    def test_ida_y_a_star_coinciden_con_ucs_en_costos_variables(self):
        azar = random.Random(981)
        for numero in range(120):
            mapa = crear_mapa(["....", "....", "....", "...E"])
            for posicion in np.ndindex(mapa.shape):
                if posicion not in ((0, 0), (3, 3)):
                    mapa[posicion].quemada = azar.random() < 0.25
                mapa[posicion].agentes = [None] * azar.randrange(mapa[posicion].capacidad + 1)
            alpha = azar.choice([0, 0.3, 1, 4])
            esperado = costo(mapa, BUSQUEDAS["ucs"](mapa, (0, 0), alpha), alpha)
            for nombre in ("a_star", "ida_star"):
                with self.subTest(caso=numero, algoritmo=nombre):
                    ruta = BUSQUEDAS[nombre](mapa, (0, 0), alpha)
                    if esperado is None:
                        self.assertIsNone(ruta)
                    else:
                        self.assertTrue(ruta_valida(mapa, (0, 0), ruta))
                        self.assertAlmostEqual(costo(mapa, ruta, alpha), esperado)

    def test_alpha_no_finito(self):
        mapa = crear_mapa([".E"])
        for nombre in ("ucs", "a_star", "ida_star"):
            for alpha in (-1, float("nan"), float("inf")):
                self.assertIsNone(BUSQUEDAS[nombre](mapa, (0, 0), alpha))

    def test_ida_reabre_celdas_y_reinicia_umbrales(self):
        mapa = crear_mapa([".....", ".###.", "...#E", "....."])
        mapa[0, 1].agentes = [None] * 4
        mapa[0, 2].agentes = [None] * 4
        esperado = BUSQUEDAS["ucs"](mapa, (0, 0), 8)
        ruta = BUSQUEDAS["ida_star"](mapa, (0, 0), 8)
        self.assertEqual(costo(mapa, ruta, 8), costo(mapa, esperado, 8))
        # Una region con ciclos y salida aislada debe terminar sin ruta.
        mapa = crear_mapa([".....", ".....", "...##", "...#E"])
        self.assertIsNone(BUSQUEDAS["ida_star"](mapa, (0, 0)))

    def test_motor_conserva_resultados_y_estados_turno_a_turno(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "mapa.txt"
            archivo.write_text("######\n#...E#\n#....#\n#....#\n######\n")
            escenario = dict(mapa=str(archivo), poblacion_inicial=12,
                             cantidad_focos=1, k=3, probabilidad=0.3, max_turnos=35)
            for algoritmo in BUSQUEDAS:
                for semilla in (1, 9):
                    nuevo = MotorSimulacion(algoritmo, escenario, semilla)
                    referencia = MotorSimulacion(PoliticaSinCache(algoritmo), escenario, semilla)
                    while not nuevo.terminada:
                        self.assertEqual(nuevo.avanzar_turno(), referencia.avanzar_turno())
                        for a, b in zip(nuevo.agentes, referencia.agentes):
                            self.assertEqual(vars(a), vars(b))

    def test_cache_dura_un_turno_y_cuenta_cada_planificacion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "mapa.txt"
            archivo.write_text("#####\n#.#E#\n#####\n")
            escenario = dict(mapa=str(archivo), poblacion_inicial=2, cantidad_focos=0,
                             posiciones_iniciales=[(1, 1), (1, 1)], max_turnos=2)
            motor = MotorSimulacion("bfs", escenario, 1)
            with patch.dict(BUSQUEDAS, {"bfs": unittest.mock.Mock(return_value=None)}):
                motor.avanzar_turno()
                self.assertEqual(BUSQUEDAS["bfs"].call_count, 1)
                motor.avanzar_turno()
                self.assertEqual(BUSQUEDAS["bfs"].call_count, 2)
            self.assertEqual(motor.resultado()["planificaciones"], 4)


if __name__ == "__main__":
    unittest.main()
