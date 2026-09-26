import csv
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.evaluation.benchmark import ejecutar_benchmark, preparar_configuracion
from src.simulation.motor import simular


class PruebasBenchmark(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.mapa = self.raiz / 'mapa.txt'
        self.mapa.write_text('...E')
        self.salida = self.raiz / 'resultados'
        self.config = {
            'modo': 'piloto', 'mapas': [str(self.mapa)], 'poblaciones': [1, 2],
            'semillas': [10, 11], 'algoritmos': ['bfs', 'a_star'],
            'parametros': {'cantidad_focos': 0, 'max_turnos': 10}
        }

    def test_matriz_reanuda_sin_duplicados_y_csv(self):
        llamadas = []
        def ejecutar(politica, escenario, semilla):
            llamadas.append((politica, escenario['poblacion_inicial'], semilla))
            return simular(politica, escenario, semilla)
        parcial = ejecutar_benchmark(self.config, self.salida, 3, ejecutar)
        self.assertEqual(parcial['completadas'], 3)
        completo = ejecutar_benchmark(self.config, self.salida, simulador=ejecutar)
        self.assertEqual(completo['completadas'], 8)
        self.assertEqual(len(llamadas), 8)
        ejecutar_benchmark(self.config, self.salida, simulador=ejecutar)
        self.assertEqual(len(llamadas), 8)
        with (self.salida / 'resultados.csv').open() as archivo:
            filas = list(csv.DictReader(archivo))
        self.assertEqual(len(filas), 8)
        self.assertEqual(len({fila['id'] for fila in filas}), 8)
        self.assertEqual({fila['semilla'] for fila in filas if fila['algoritmo'] == 'bfs'}, {'10', '11'})

    def test_cambio_parametros_o_mapa_no_mezcla_corridas(self):
        ejecutar_benchmark(self.config, self.salida, 1)
        otra = deepcopy(self.config)
        otra['parametros']['k'] = 5
        with self.assertRaises(ValueError):
            ejecutar_benchmark(otra, self.salida)
        self.mapa.write_text('....E')
        with self.assertRaises(ValueError):
            ejecutar_benchmark(self.config, self.salida)
        self.assertEqual(len(list((self.salida / 'corridas').glob('*.json'))), 1)

    def test_error_no_cuenta_como_ejecucion_y_se_reintenta(self):
        def fallar(*args):
            raise RuntimeError('fallo de prueba')
        progreso = ejecutar_benchmark(self.config, self.salida, 1, fallar)
        self.assertEqual(progreso['completadas'], 0)
        self.assertEqual(progreso['errores_esta_invocacion'], 1)
        self.assertEqual(len(list((self.salida / 'errores').glob('*.json'))), 1)
        progreso = ejecutar_benchmark(self.config, self.salida)
        self.assertEqual(progreso['completadas'], 8)

    def test_interrupcion_conserva_corridas_y_continua(self):
        llamadas = 0
        def interrumpir(politica, escenario, semilla):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise KeyboardInterrupt()
            return simular(politica, escenario, semilla)
        with self.assertRaises(KeyboardInterrupt):
            ejecutar_benchmark(self.config, self.salida, simulador=interrumpir)
        progreso = json.loads((self.salida / 'progreso.json').read_text())
        self.assertEqual(progreso['completadas'], 1)
        self.assertEqual(ejecutar_benchmark(self.config, self.salida)['completadas'], 8)

    def test_resultado_corrupto_no_se_acepta(self):
        ejecutar_benchmark(self.config, self.salida, 1)
        archivo = next((self.salida / 'corridas').glob('*.json'))
        registro = json.loads(archivo.read_text())
        registro['resultado']['evacuados'] = 500
        archivo.write_text(json.dumps(registro))
        with self.assertRaises(ValueError):
            ejecutar_benchmark(self.config, self.salida)

    def test_validacion_y_minimo_final(self):
        for campo, valor in [('semillas', [1, 1]), ('poblaciones', [0]), ('algoritmos', ['invalido'])]:
            config = deepcopy(self.config)
            config[campo] = valor
            with self.assertRaises(ValueError):
                preparar_configuracion(config)
        final = deepcopy(self.config)
        final['modo'] = 'final'
        with self.assertRaises(ValueError):
            preparar_configuracion(final)
        config = deepcopy(self.config)
        config['parametros']['k'] = 0
        with self.assertRaises(ValueError):
            preparar_configuracion(config)

    def test_genetico_guardado_y_semillas_separadas(self):
        politica = self.raiz / 'politica.json'
        politica.write_text(json.dumps({
            'parametros': {'peso_congestion': 2, 'peso_riesgo': 3, 'umbral_bloqueo': 2},
            'semillas_entrenamiento': [1, 2]
        }))
        config = deepcopy(self.config)
        config['algoritmos'] = ['genetico']
        config['politica_genetica'] = str(politica)
        self.assertEqual(ejecutar_benchmark(config, self.salida)['completadas'], 4)
        config['semillas'] = [2]
        with self.assertRaises(ValueError):
            preparar_configuracion(config)


if __name__ == '__main__':
    unittest.main()
