import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.evaluation.benchmark import (
    construir_casos, ejecutar_benchmark, regenerar_reporte,
)
from src.evaluation.reporte import generar_reporte
from src.simulation.motor import VALORES_INICIALES


class TestReporteBenchmark(unittest.TestCase):
    def configuracion(self, mapa):
        return {
            "modo": "piloto", "mapas": [str(mapa)], "poblaciones": [1],
            "semillas": [1, 2, 3], "algoritmos": ["bfs"],
            "parametros": dict(VALORES_INICIALES, cantidad_focos=0, max_turnos=10),
        }

    def test_estadisticas_excluyen_tiempos_sin_evacuados(self):
        config = self.configuracion("mapa.txt")
        casos = construir_casos(config)
        registros = {}
        for caso, supervivencia, turno in zip(casos, [0.1, 0.3, 0], [20, 40, None]):
            registros[caso["id"]] = {
                "segundos_ejecucion": 60,
                "resultado": {"supervivencia": supervivencia,
                              "turno_ultimo_evacuado": turno,
                              "motivo_termino": "max_turnos"},
            }
        reporte = generar_reporte(config, casos, registros)
        fila = next(linea for linea in reporte.splitlines() if linea.startswith("Mapa 1 ") and "|" in linea)
        self.assertEqual([campo.strip() for campo in fila.split("|")],
                         ["Mapa 1", "BFS", "13.33%", "30.00", "14.14", "20", "40"])
        self.assertIn("Tiempo total: 3.00 minutos", reporte)
        self.assertIn("tiempos validos=2 | sin evacuados=1 | limite de turnos=3", reporte)

    def test_reporte_vacio_y_agrupacion(self):
        config = self.configuracion("mapa.txt")
        config["mapas"].append("otro.txt")
        config["poblaciones"].append(2)
        config["algoritmos"].append("ida_star")
        reporte = generar_reporte(config, construir_casos(config), {})
        self.assertIn("PARCIAL | Corridas completadas: 0/24", reporte)
        self.assertEqual(reporte.count("Configuracion:"), 2)
        self.assertEqual(reporte.count("|        N/D |"), 8)

    def test_ejecucion_reanudacion_y_exportacion_historica(self):
        with tempfile.TemporaryDirectory() as carpeta:
            mapa = Path(carpeta) / "mapa.txt"
            mapa.write_text("#####\n#..E#\n#####\n", encoding="utf-8")
            config = self.configuracion(mapa)
            salida = Path(carpeta) / "resultados"
            with contextlib.redirect_stdout(io.StringIO()):
                ejecutar_benchmark(config, salida, limite_ejecuciones=1)
                parcial = (salida / "reporte_benchmark.txt").read_text()
                self.assertIn("PARCIAL | Corridas completadas: 1/3", parcial)
                self.assertIn("100.00%", parcial)
                self.assertIn("N/D", parcial)  # Una observacion no tiene Std muestral.
                progreso = ejecutar_benchmark(config, salida)
            self.assertEqual(progreso["completadas"], 3)
            reporte = salida / "reporte_benchmark.txt"
            contenido = reporte.read_bytes()
            self.assertIn(b"COMPLETO", contenido)
            originales = {p: p.read_bytes() for p in salida.rglob("*.json")}
            segundos = sum(json.loads(p.read_text())["segundos_ejecucion"]
                           for p in (salida / "corridas").glob("*.json"))
            self.assertIn(f"Tiempo total: {segundos / 60:.2f} minutos", contenido.decode())
            mapa.unlink()  # Exportar no depende de que los mapas sigan disponibles.
            reporte.unlink()
            with patch("src.evaluation.benchmark.preparar_configuracion", side_effect=AssertionError):
                self.assertEqual(regenerar_reporte(salida), reporte)
            self.assertEqual(reporte.read_bytes(), contenido)
            for archivo, original in originales.items():
                self.assertEqual(archivo.read_bytes(), original)

    def test_interrupcion_y_error_no_inventan_resultados(self):
        with tempfile.TemporaryDirectory() as carpeta:
            mapa = Path(carpeta) / "mapa.txt"
            mapa.write_text("#####\n#..E#\n#####\n", encoding="utf-8")
            salida = Path(carpeta) / "resultados"
            simulador = unittest.mock.Mock(side_effect=[ValueError("fallo de prueba"), KeyboardInterrupt])
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(KeyboardInterrupt):
                ejecutar_benchmark(self.configuracion(mapa), salida, simulador=simulador)
            reporte = (salida / "reporte_benchmark.txt").read_text()
            self.assertIn("PARCIAL | Corridas completadas: 0/3", reporte)
            self.assertNotIn("0.00%", reporte)
            self.assertEqual(json.loads((salida / "progreso.json").read_text())["errores_esta_invocacion"], 1)


if __name__ == "__main__":
    unittest.main()
