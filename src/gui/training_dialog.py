"""Entrenamiento independiente de la evaluación, usando los perfiles compartidos."""
import re
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from src.evaluation.benchmark import preparar_configuracion, guardar_json
from .experimentos import RAIZ, estado_compartido, semillas_reservadas, nuevo_destino, validar_politica
from .perfil_widget import PerfilWidget, enteros
from .proceso import Proceso


class TrainingDialog(QtWidgets.QDialog):
    politica_entrenada_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado_gui = estado_compartido(parent)
        self.setWindowTitle('Entrenar estrategia genética')
        self.resize(940, 850)
        self._cerrar_pendiente = False
        self._salida_ejecucion = None
        self.control = Proceso(self.estado_gui, self)
        self.control.linea.connect(self._linea)
        self.control.terminado.connect(self._finalizado)
        layout = QtWidgets.QVBoxLayout(self)
        descripcion = QtWidgets.QLabel('Optimiza congestión, riesgo y bloqueo mediante selección, cruce uniforme y mutación.\n'
                                       'La población evolutiva son estrategias, no personas. Se guarda solo al terminar; detener pierde el avance no guardado.')
        descripcion.setWordWrap(True)
        layout.addWidget(descripcion)
        self.perfil = PerfilWidget(self.estado_gui, self)
        self.perfil.algoritmos.parentWidget().hide()
        layout.addWidget(self.perfil)
        self.formulario = QtWidgets.QWidget()
        forma = QtWidgets.QFormLayout(self.formulario)
        self.spin_poblacion = QtWidgets.QSpinBox()
        self.spin_poblacion.setRange(3, 1000)
        self.spin_poblacion.setValue(10)
        self.spin_generaciones = QtWidgets.QSpinBox()
        self.spin_generaciones.setRange(1, 1000)
        self.spin_generaciones.setValue(5)
        self.spin_semilla = QtWidgets.QSpinBox()
        self.spin_semilla.setRange(0, 2147483647)
        self.spin_semilla.setValue(42)
        self.txt_semillas = QtWidgets.QLineEdit('1000 1001 1002 1003 1004')
        self.txt_salida = QtWidgets.QLineEdit(str(nuevo_destino(RAIZ / 'results/policies', 'entrenamiento') / 'politica.json'))
        forma.addRow('Estrategias por generación', self.spin_poblacion)
        forma.addRow('Generaciones', self.spin_generaciones)
        forma.addRow('Semilla evolutiva', self.spin_semilla)
        forma.addRow('Semillas de entrenamiento', self.txt_semillas)
        forma.addRow('Archivo nuevo de política', self.txt_salida)
        layout.addWidget(self.formulario)
        self.lbl_estimacion = QtWidgets.QLabel()
        layout.addWidget(self.lbl_estimacion)
        self.btn_iniciar = QtWidgets.QPushButton('Iniciar entrenamiento')
        self.btn_detener = QtWidgets.QPushButton('Detener sin guardar modelo')
        self.btn_detener.setEnabled(False)
        self.btn_iniciar.clicked.connect(self._iniciar_entrenamiento)
        self.btn_detener.clicked.connect(self.control.detener)
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.btn_iniciar)
        fila.addWidget(self.btn_detener)
        layout.addLayout(fila)
        self.barra_progreso = QtWidgets.QProgressBar()
        layout.addWidget(self.barra_progreso)
        self.lbl_estado = QtWidgets.QLabel('Listo para entrenar.')
        layout.addWidget(self.lbl_estado)
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(3000)
        layout.addWidget(self.txt_log, 1)
        self.perfil.cambiado.connect(self._estimar)
        self.txt_semillas.textChanged.connect(self._estimar)
        self.spin_poblacion.valueChanged.connect(self._estimar)
        self.spin_generaciones.valueChanged.connect(self._estimar)
        self._estimar()

    def _estimar(self, *args):
        try:
            c = self.perfil.configuracion()
            n = len(c['mapas']) * len(c['poblaciones']) * len(enteros(self.txt_semillas.text()))
            n *= self.spin_poblacion.value() * self.spin_generaciones.value()
            self.perfil.resumen.setText(f"Entrenamiento: {len(c['mapas'])} mapas × {len(c['poblaciones'])} poblaciones de personas. Las semillas de evaluación quedan reservadas.")
            self.lbl_estimacion.setText(f'Hasta {n} simulaciones; las estrategias repetidas reutilizan su evaluación.')
        except (ValueError, KeyError):
            self.lbl_estimacion.setText('Revisa la selección y las semillas.')

    def iniciar_configuracion(self, config, salida, semillas, poblacion, generaciones, semilla_genetica=42):
        if self.estado_gui.ocupado is not None:
            raise ValueError('Ya hay un cálculo activo.')
        salida = Path(salida).resolve()
        if salida.exists():
            raise ValueError('La política de destino ya existe. Usa un archivo nuevo.')
        if not semillas or any(type(s) is not int for s in semillas) or len(set(semillas)) != len(semillas):
            raise ValueError('Las semillas deben ser enteros distintos.')
        if set(semillas) & (semillas_reservadas() | set(config['semillas'])):
            raise ValueError('Las semillas se solapan con las reservas de evaluación.')
        if poblacion < 3 or generaciones < 1:
            raise ValueError('Se requieren al menos 3 estrategias y 1 generación.')
        config = config.copy()
        config['algoritmos'] = ['bfs']  # Solo se valida el escenario; entrenar usa la política genética.
        config.pop('politica_genetica', None)
        config, _ = preparar_configuracion(config)
        configuracion = nuevo_destino(salida.parent, 'config_entrenamiento').with_suffix('.json')
        guardar_json(configuracion, config)
        self._salida_ejecucion = salida
        self.txt_log.clear()
        self.barra_progreso.setValue(0)
        self.control.iniciar([str(RAIZ / 'scripts/train_genetic.py'), '--config', str(configuracion),
                              '--salida', str(salida), '--poblacion', str(poblacion),
                              '--generaciones', str(generaciones), '--semilla-genetica', str(semilla_genetica),
                              '--semillas', *map(str, semillas)])
        self._bloquear(True)
        self.lbl_estado.setText('Entrenando. El máximo de simulaciones es una cota, no una cantidad obligatoria.')

    def _iniciar_entrenamiento(self):
        try:
            if not self.txt_salida.text().strip():
                raise ValueError('Indica un archivo de salida.')
            self.iniciar_configuracion(self.perfil.configuracion(), self.txt_salida.text(),
                                      enteros(self.txt_semillas.text()), self.spin_poblacion.value(),
                                      self.spin_generaciones.value(), self.spin_semilla.value())
        except (ValueError, OSError, TypeError, KeyError) as error:
            QtWidgets.QMessageBox.warning(self, 'No se inició', str(error))

    def _bloquear(self, activo):
        self.perfil.setEnabled(not activo)
        self.formulario.setEnabled(not activo)
        self.btn_iniciar.setEnabled(not activo)
        self.btn_detener.setEnabled(activo)

    def _linea(self, linea):
        self.txt_log.appendPlainText(linea)
        if self._salida_ejecucion:
            with (self._salida_ejecucion.parent / "entrenamiento.log").open("a", encoding="utf-8") as archivo:
                archivo.write(linea + "\n")
        match = re.search(r'Simulaciones ejecutadas:\s*(\d+)\s*\(máximo\s*(\d+)\)', linea)
        if match:
            actual, total = map(int, match.groups())
            self.barra_progreso.setValue(min(99, int(100 * actual / max(1, total))))
            self.lbl_estado.setText(f'{actual}/{total} simulaciones como máximo; las repetidas se reutilizan.')

    def _finalizado(self, codigo, cancelado):
        self._bloquear(False)
        if cancelado:
            self.lbl_estado.setText('Entrenamiento detenido; el progreso no guardado no se puede reanudar.')
        elif codigo != 0:
            self.lbl_estado.setText(f'Entrenamiento fallido (código {codigo}). Revisa el registro.')
        else:
            try:
                validar_politica(self._salida_ejecucion, semillas_reservadas())
                self.estado_gui.elegir_politica(self._salida_ejecucion)
                self.politica_entrenada_signal.emit(str(self._salida_ejecucion))
                self.barra_progreso.setValue(100)
                self.lbl_estado.setText('Política validada y disponible en simulación y benchmark: ' + str(self._salida_ejecucion))
                self.txt_salida.setText(str(nuevo_destino(RAIZ / 'results/policies', 'entrenamiento') / 'politica.json'))
            except (ValueError, OSError, TypeError, KeyError) as error:
                self.lbl_estado.setText('La política no se activó: ' + str(error))
        if self._cerrar_pendiente:
            self.close()

    def closeEvent(self, event):
        if self.control.activo:
            respuesta = QtWidgets.QMessageBox.question(self, 'Detener entrenamiento', 'El entrenamiento no guarda avances intermedios. ¿Detenerlo y cerrar?')
            if respuesta == QtWidgets.QMessageBox.Yes:
                self._cerrar_pendiente = True
                self.control.detener()
            event.ignore()
        else:
            event.accept()
