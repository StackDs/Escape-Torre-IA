import json
import random
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.models.mapa import cargar_mapa
from src.models.agente import State
from src.simulation.motor import MotorSimulacion, simular
from src.simulation.movimiento import resolver_movimientos, aplicar_movimientos
from src.simulation.politicas import PoliticaBusqueda, BUSQUEDAS
from src.algorithms.Genetic.individuo import Individuo
from src.algorithms.Genetic.politica import PoliticaGenetica
from src.evaluation.train_genetic import entrenar


class PruebasMotor(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.directorio = Path(self.temporal.name)
        self.indice = 0

    def escenario(self, texto='...E', **parametros):
        self.indice += 1
        archivo = self.directorio / (str(self.indice) + '.txt')
        archivo.write_text(texto, encoding='utf-8')
        escenario = {
            'mapa': str(archivo), 'poblacion_inicial': 1,
            'posiciones_iniciales': [[0, 0]], 'focos': [], 'max_turnos': 20
        }
        escenario.update(parametros)
        return escenario

    def invariantes(self, motor):
        presentes = []
        for posicion, celda in np.ndenumerate(motor.mapa):
            self.assertLessEqual(len(celda.agentes), celda.capacidad)
            for agente in celda.agentes:
                presentes.append(agente.id_agente)
                self.assertEqual(agente.obtener_posicion(), posicion)
                self.assertIn(agente.estado, (State.ACTIVO, State.ESPERANDO))
                self.assertFalse(celda.quemada)
        vivos = [a.id_agente for a in motor.agentes if a.estado in (State.ACTIVO, State.ESPERANDO)]
        self.assertEqual(sorted(presentes), sorted(vivos))
        self.assertEqual(len(presentes), len(set(presentes)))
        resultado = motor.resultado()
        self.assertEqual(resultado['evacuados'] + resultado['fallecidos'] + resultado['pendientes'], len(motor.agentes))

    def test_seis_busquedas_y_genetico_evacuacion_conocida(self):
        politicas = list(BUSQUEDAS) + [PoliticaGenetica(Individuo(2, 5, 3))]
        for politica in politicas:
            with self.subTest(politica=politica):
                motor = MotorSimulacion(politica, self.escenario(), 7)
                for turno in range(1, 4):
                    resultado = motor.avanzar_turno()
                    self.assertEqual(motor.turno, turno)
                    self.assertEqual(motor.agentes[0].movimientos, turno)
                    self.invariantes(motor)
                self.assertEqual(resultado['evacuados'], 1)
                self.assertEqual(resultado['turno_ultimo_evacuado'], 3)
                self.assertEqual(resultado['planificaciones'], 1)
                self.assertEqual(resultado['esperas'], 0)
                estado_azar = motor.azar_fuego.getstate()
                self.assertEqual(motor.avanzar_turno(), resultado)
                self.assertEqual(motor.ejecutar(), resultado)
                self.assertEqual(motor.azar_fuego.getstate(), estado_azar)

    def test_no_aprovecha_celda_que_se_desocupa(self):
        escenario = self.escenario('..E', poblacion_inicial=2,
                                   posiciones_iniciales=[[0, 0], [0, 1]], capacidad_pasillos=1)
        motor = MotorSimulacion('bfs', escenario, 3)
        primero = motor.avanzar_turno()
        self.assertEqual(primero['evacuados'], 1)
        self.assertEqual(motor.agentes[0].obtener_posicion(), (0, 0))
        self.assertEqual(motor.agentes[0].ruta, [(0, 1), (0, 2)])
        self.assertEqual(motor.agentes[0].turnos_bloqueado, 1)
        self.invariantes(motor)
        motor.avanzar_turno()
        self.assertEqual(motor.agentes[0].obtener_posicion(), (0, 1))
        self.assertEqual(motor.agentes[0].turnos_bloqueado, 0)
        self.assertEqual(motor.ejecutar()['turno_ultimo_evacuado'], 3)

    def test_intercambio_entre_celdas_llenas_rechazado(self):
        motor = MotorSimulacion('bfs', self.escenario('..E', poblacion_inicial=2,
            posiciones_iniciales=[[0, 0], [0, 1]], capacidad_pasillos=1), 4)
        motor.agentes[0].asignar_ruta([(0, 1), (0, 2)])
        motor.agentes[1].asignar_ruta([(0, 0), (0, 1), (0, 2)])
        self.assertEqual(resolver_movimientos(motor.mapa, motor.agentes, random.Random(0)), set())

    def test_conflicto_por_pasillo_y_orden_de_agentes(self):
        motor = MotorSimulacion('bfs', self.escenario('...\n#.#\n#E#', poblacion_inicial=2,
            posiciones_iniciales=[[0, 0], [0, 2]], capacidad_pasillos=1), 8)
        for agente in motor.agentes:
            agente.asignar_ruta([(0, 1), (1, 1), (2, 1)])
        a = resolver_movimientos(motor.mapa, motor.agentes, random.Random(5))
        b = resolver_movimientos(motor.mapa, list(reversed(motor.agentes)), random.Random(5))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 1)
        aplicar_movimientos(motor.mapa, motor.agentes, a, 1)
        self.invariantes(motor)
        self.assertEqual(sum(x.movimientos for x in motor.agentes), 1)
        self.assertEqual(sum(x.esperas for x in motor.agentes), 1)

    def test_salida_no_reutiliza_cupos(self):
        motor = MotorSimulacion('bfs', self.escenario('.E', poblacion_inicial=4,
            posiciones_iniciales=[[0, 0]] * 4), 1)
        primero = motor.avanzar_turno()
        self.assertEqual(primero['evacuados'], 2)
        self.assertEqual(primero['pendientes'], 2)
        self.assertEqual(len(motor.mapa[0, 1].agentes), 0)
        self.invariantes(motor)
        segundo = motor.avanzar_turno()
        self.assertEqual(segundo['evacuados'], 4)
        self.assertEqual(segundo['turno_ultimo_evacuado'], 2)

    def test_muerte_antes_de_mover_y_retirada_de_celda(self):
        motor = MotorSimulacion('bfs', self.escenario('..E', posiciones_iniciales=[[0, 1]],
            focos=[[0, 0]], k=1, probabilidad=1), 0)
        resultado = motor.avanzar_turno()
        self.assertEqual(resultado['fallecidos'], 1)
        self.assertEqual(resultado['movimientos'], 0)
        self.assertEqual(resultado['planificaciones'], 0)
        self.assertIsNone(resultado['turno_ultimo_evacuado'])
        self.assertEqual(motor.agentes[0].turno_fallecimiento, 1)
        self.invariantes(motor)

    def test_incendio_invalida_ruta_y_busqueda_fallida_cuenta(self):
        motor = MotorSimulacion('bfs', self.escenario('...E\n##.#', focos=[[1, 2]],
            k=2, probabilidad=1), 0)
        motor.avanzar_turno()
        self.assertEqual(motor.agentes[0].obtener_posicion(), (0, 1))
        segundo = motor.avanzar_turno()
        self.assertEqual(segundo['planificaciones'], 2)
        self.assertEqual(motor.agentes[0].ruta, [])
        self.assertEqual(motor.agentes[0].estado, State.ESPERANDO)
        self.assertEqual(segundo['fallecidos'], 0)
        motor.avanzar_turno()
        self.assertEqual(motor.resultado()['planificaciones'], 3)
        self.invariantes(motor)

    def test_sin_ruta_termina_con_pendientes(self):
        motor = MotorSimulacion('bfs', self.escenario('.#E', max_turnos=3), 0)
        resultado = motor.ejecutar()
        self.assertEqual(resultado['pendientes'], 1)
        self.assertEqual(resultado['fallecidos'], 0)
        self.assertEqual(resultado['planificaciones'], 3)
        self.assertEqual(resultado['esperas'], 3)
        self.assertEqual(resultado['motivo_termino'], 'max_turnos')
        self.assertIsNone(resultado['turno_ultimo_evacuado'])

    def test_replanificacion_al_umbral_no_duplica_contador(self):
        motor = MotorSimulacion('bfs', self.escenario('.E', poblacion_inicial=4,
            posiciones_iniciales=[[0, 0]] * 4, capacidad_salida=1, umbral_bloqueo=2), 3)
        motor.avanzar_turno()
        motor.avanzar_turno()
        self.assertEqual(motor.resultado()['planificaciones'], 4)
        motor.avanzar_turno()
        self.assertEqual(motor.resultado()['planificaciones'], 6)
        self.invariantes(motor)

    def test_reproducibilidad_inicializacion_y_fuego_entre_politicas(self):
        escenario = self.escenario('.......\n.......\n......E', poblacion_inicial=6,
                                   max_turnos=5, k=1, probabilidad=0.4, cantidad_focos=2)
        del escenario['focos']
        del escenario['posiciones_iniciales']
        original = deepcopy(escenario)
        motores = [MotorSimulacion(nombre, escenario, 42) for nombre in ('bfs', 'bfs', 'dfs')]
        for motor in motores[1:]:
            self.assertEqual(motor.focos, motores[0].focos)
            self.assertEqual(motor.posiciones_iniciales, motores[0].posiciones_iniciales)
        for _ in range(5):
            if any(m.terminada for m in motores):
                break
            resultados = [m.avanzar_turno() for m in motores]
            self.assertEqual(resultados[0], resultados[1])
            fuegos = [[c.quemada for c in m.mapa.flat] for m in motores]
            self.assertEqual(fuegos[0], fuegos[2])
            for motor in motores:
                self.invariantes(motor)
        self.assertEqual(escenario, original)
        self.assertIsNot(motores[0].mapa[0, 0], motores[1].mapa[0, 0])

    def test_focos_aleatorios_excluyen_posiciones_manuales(self):
        escenario = self.escenario('...E', cantidad_focos=2)
        del escenario['focos']
        motor = MotorSimulacion('bfs', escenario, 10)
        self.assertEqual(motor.focos, [(0, 1), (0, 2)])

    def test_posiciones_automaticas_respetan_capacidad(self):
        escenario = self.escenario('...E', poblacion_inicial=4, focos=[[0, 0]], capacidad_pasillos=2)
        del escenario['posiciones_iniciales']
        motor = MotorSimulacion('bfs', escenario, 10)
        self.assertEqual(len(motor.mapa[0, 1].agentes), 2)
        self.assertEqual(len(motor.mapa[0, 2].agentes), 2)
        self.invariantes(motor)

    def test_cargador_rechaza_mapas_invalidos(self):
        for texto in ('', '..\n.', '.XE', '..', 'EE'):
            escenario = self.escenario(texto)
            with self.assertRaises(ValueError):
                cargar_mapa(escenario['mapa'])

    def test_configuraciones_invalidas(self):
        for cambios in ({'k': 0}, {'probabilidad': 2}, {'max_turnos': 0},
                        {'poblacion_inicial': 0}, {'capacidad_pasillos': 0},
                        {'alpha': float('nan')}, {'focos': [[0, 3]]},
                        {'focos': [[0, 0]]}, {'focos': [[0, 1], [0, 1]]},
                        {'posiciones_iniciales': [[-1, 0]]},
                        {'posiciones_iniciales': [[0, 3]]},
                        {'focos': None}, {'posiciones_iniciales': None}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                MotorSimulacion('bfs', self.escenario(**cambios), 0)
        with self.assertRaises(ValueError):
            MotorSimulacion('desconocido', self.escenario(), 0)
        escenario = self.escenario('.E', poblacion_inicial=5)
        del escenario['posiciones_iniciales']
        with self.assertRaises(ValueError):
            MotorSimulacion('bfs', escenario, 0)

    def test_detecta_none_del_modulo_de_fuego(self):
        motor = MotorSimulacion('bfs', self.escenario(), 0)
        with patch('src.simulation.motor.propagar_fuego', return_value=None):
            with self.assertRaises(ValueError):
                motor.avanzar_turno()

    def test_entrenamiento_con_motor_real(self):
        escenario = self.escenario('...E', max_turnos=10)
        archivo = self.directorio / 'mejor.json'
        mejor, historial = entrenar(simular, [escenario], [1, 2], [100], archivo,
            {'tamano_poblacion': 3, 'generaciones': 2, 'semilla': 42})
        self.assertEqual(mejor.aptitud, 1)
        self.assertEqual(len(historial), 2)
        self.assertEqual(json.loads(archivo.read_text())['aptitud_entrenamiento'], 1)
        evaluacion = simular(PoliticaGenetica(mejor), escenario, 100)
        self.assertEqual(evaluacion['evacuados'], 1)


if __name__ == '__main__':
    unittest.main()
