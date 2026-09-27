"""Aplicación principal de la interfaz gráfica PyQt5 para Escape de la Torre IA."""

import os
import sys
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets

from src.gui.benchmark_dialog import BenchmarkDialog
from src.gui.simulation_view import SimulationView
from src.gui.start_screen import StartScreen
from src.gui.theme import aplicar_tema
from src.gui.training_dialog import TrainingDialog
from src.gui.experimentos import EstadoGUI

RAIZ = Path(__file__).resolve().parents[2]


class MainWindow(QtWidgets.QMainWindow):
    """Ventana principal que gestiona las vistas de Inicio y Simulación."""

    def __init__(self, algoritmo_inicial=None, mapa_inicial=None):
        super().__init__()
        self.estado_gui = EstadoGUI(self)
        self._cerrar_pendiente = False
        self.setWindowTitle("Escape de la Torre IA - Simulador y Benchmark")
        self.resize(1360, 860)
        self.setMinimumSize(1024, 760)

        # Widget apilado para alternar entre pantalla de inicio y vista de simulación
        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)

        # Pantalla 0: Inicio
        self.start_screen = StartScreen(self)
        self.start_screen.iniciar_simulacion_signal.connect(self._mostrar_simulacion)
        self.start_screen.abrir_benchmark_signal.connect(self._abrir_benchmark)
        self.start_screen.abrir_entrenamiento_signal.connect(self._abrir_entrenamiento)
        self.stack.addWidget(self.start_screen)

        # Pantalla 1: Simulación
        self.sim_view = SimulationView(self)
        self.sim_view.volver_inicio_signal.connect(self._mostrar_inicio)
        self.stack.addWidget(self.sim_view)

        # Configurar algoritmo o mapa inicial si fueron provistos
        if algoritmo_inicial:
            self.start_screen.set_algoritmo(algoritmo_inicial)
        if mapa_inicial:
            self.start_screen.set_mapa(mapa_inicial)

        if algoritmo_inicial and mapa_inicial:
            self.sim_view.configurar_escenario_inicial(algoritmo_inicial, mapa_inicial)
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(0)

    def _mostrar_simulacion(self, algoritmo_codigo, ruta_mapa):
        self.sim_view.configurar_escenario_inicial(algoritmo_codigo, ruta_mapa)
        self.stack.setCurrentIndex(1)

    def _mostrar_inicio(self):
        self.stack.setCurrentIndex(0)

    def _abrir_benchmark(self):
        self.sim_view.detener_animacion()
        dialogo = BenchmarkDialog(self)
        dialogo.exec_()

    def _abrir_entrenamiento(self):
        self.sim_view.detener_animacion()
        dialogo = TrainingDialog(self)
        dialogo.exec_()

    def closeEvent(self, event):
        if self.sim_view._trabajador is not None:
            respuesta = QtWidgets.QMessageBox.question(self, 'Cálculo activo', '¿Detener y cerrar al terminar el turno actual?')
            if respuesta == QtWidgets.QMessageBox.Yes:
                self.sim_view.detener_animacion()
                self.sim_view._trabajador.requestInterruption()
                if not self._cerrar_pendiente:
                    self._cerrar_pendiente = True
                    self.sim_view._trabajador.finished.connect(lambda: QtCore.QTimer.singleShot(0, self.close))
            event.ignore()
        else:
            event.accept()


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Lanzador de la interfaz gráfica de Escape de la Torre IA")
    parser.add_argument("--algoritmo", help="Algoritmo inicial (bfs, dfs, ucs, a_star, greedy, ida_star, genetico)")
    parser.add_argument("--mapa", help="Ruta al mapa inicial")
    parser.add_argument("--entrenar", action="store_true", help="Abrir e iniciar el entrenamiento con los valores de la GUI")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Soporte para pantallas de alta densidad de píxeles
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication.instance()
    creado = False
    if app is None:
        app = QtWidgets.QApplication([sys.argv[0]])
        creado = True

    aplicar_tema(app)

    ventana = MainWindow(algoritmo_inicial=args.algoritmo, mapa_inicial=args.mapa)
    ventana.show()
    if args.entrenar:
        def iniciar_entrenamiento_visible():
            dialogo = TrainingDialog(ventana)
            ventana.entrenamiento_visible = dialogo
            dialogo.setModal(True)
            dialogo.show()
            dialogo.raise_()
            dialogo.activateWindow()
            QtCore.QTimer.singleShot(100, dialogo._iniciar_entrenamiento)
        QtCore.QTimer.singleShot(0, iniciar_entrenamiento_visible)

    if creado:
        return app.exec_()
    return 0


if __name__ == "__main__":
    sys.exit(main())
