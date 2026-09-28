"""Benchmarks oficiales, copias personales y cola secuencial de ambientes."""
import json
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from src.evaluation.benchmark import preparar_configuracion, guardar_json, regenerar_reporte
from .experimentos import RAIZ, AMBIENTES, cargar_perfil, estado_compartido, nuevo_destino, validar_politica
from .perfil_widget import PerfilWidget
from .proceso import Proceso


class BenchmarkDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, politica_actual=None):
        super().__init__(parent)
        self.estado_gui = estado_compartido(parent)
        self.setWindowTitle('Experimentos de evacuación')
        self.resize(980, 880)
        self.cola = []
        self.trabajos = []
        self.actual = None
        self._solo_reporte = False
        self._cerrar_pendiente = False
        self.control = Proceso(self.estado_gui, self)
        self.control.linea.connect(self._agregar_log)
        self.control.terminado.connect(self._finalizado)
        layout = QtWidgets.QVBoxLayout(self)
        self.perfil = PerfilWidget(self.estado_gui, self)
        layout.addWidget(self.perfil)
        self.txt_politica = QtWidgets.QLineEdit(politica_actual or self.estado_gui.politica)
        self.btn_politica = QtWidgets.QPushButton('Elegir política entrenada')
        self.btn_politica.clicked.connect(self._elegir_politica)
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(self.txt_politica, 1)
        fila.addWidget(self.btn_politica)
        layout.addLayout(fila)
        self.txt_salida = QtWidgets.QLineEdit(str(nuevo_destino(RAIZ / 'results/raw/gui', 'experimento')))
        self.btn_salida = QtWidgets.QPushButton('Carpeta nueva…')
        self.btn_salida.clicked.connect(self._elegir_salida)
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(QtWidgets.QLabel('Destino del lote'))
        fila.addWidget(self.txt_salida, 1)
        fila.addWidget(self.btn_salida)
        layout.addLayout(fila)
        self.btn_iniciar = QtWidgets.QPushButton('Ejecutar selección')
        self.btn_reanudar = QtWidgets.QPushButton('Reanudar manifiesto…')
        self.btn_detener = QtWidgets.QPushButton('Detener y conservar runs')
        self.btn_detener.setEnabled(False)
        self.btn_iniciar.clicked.connect(self._iniciar_benchmark)
        self.btn_reanudar.clicked.connect(self._elegir_reanudacion)
        self.btn_detener.clicked.connect(self._detener_benchmark)
        fila = QtWidgets.QHBoxLayout()
        for b in (self.btn_iniciar, self.btn_reanudar, self.btn_detener):
            fila.addWidget(b)
        layout.addLayout(fila)
        self.barra_progreso = QtWidgets.QProgressBar()
        self.barra_lote = QtWidgets.QProgressBar()
        self.barra_progreso.setFormat('Escenario: %p%')
        self.barra_lote.setFormat('Lote: %p%')
        layout.addWidget(self.barra_progreso)
        layout.addWidget(self.barra_lote)
        self.lbl_estado = QtWidgets.QLabel('Listo. Revisa la selección y el destino antes de ejecutar.')
        self.lbl_estado.setWordWrap(True)
        layout.addWidget(self.lbl_estado)
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(3000)
        layout.addWidget(self.txt_log, 1)
        self.resultados = QtWidgets.QComboBox()
        self.btn_ver = QtWidgets.QPushButton('Ver reporte TXT')
        self.btn_abrir = QtWidgets.QPushButton('Abrir carpeta')
        self.btn_reporte = QtWidgets.QPushButton('Regenerar reporte')
        self.btn_cargar_resultado = QtWidgets.QPushButton('Cargar resultados…')
        fila = QtWidgets.QHBoxLayout()
        for w in (self.resultados, self.btn_ver, self.btn_abrir, self.btn_reporte, self.btn_cargar_resultado):
            fila.addWidget(w)
        layout.addLayout(fila)
        self.btn_ver.clicked.connect(self._ver_reporte)
        self.btn_abrir.clicked.connect(self._abrir_carpeta)
        self.btn_reporte.clicked.connect(self._regenerar)
        self.btn_cargar_resultado.clicked.connect(self._cargar_resultados)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(300)
        self.timer.timeout.connect(self._actualizar_progreso)
        self.perfil.cambiado.connect(self._actualizar_botones)
        self._actualizar_botones()

    def _actualizar_botones(self):
        activo = self.control.activo or bool(self.cola)
        for w in (self.perfil, self.txt_politica, self.btn_politica, self.txt_salida, self.btn_salida,
                  self.btn_iniciar, self.btn_reanudar, self.btn_cargar_resultado):
            w.setEnabled(not activo)
        self.btn_reporte.setEnabled(not activo)
        self.btn_detener.setEnabled(activo)

    def _elegir_politica(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Política entrenada', str(RAIZ / 'results/policies'), 'JSON (*.json)')
        if ruta:
            self.txt_politica.setText(ruta)

    def _elegir_salida(self):
        ruta = QtWidgets.QFileDialog.getExistingDirectory(self, 'Carpeta contenedora', str(RAIZ / 'results'))
        if ruta:
            self.txt_salida.setText(str(nuevo_destino(ruta, 'experimento')))

    def preparar_trabajos(self):
        seleccion = self.perfil.configuracion()
        if seleccion['modo'] != 'final' or len(seleccion['semillas']) < 80:
            raise ValueError('Los nuevos benchmarks requieren al menos 80 repeticiones finales. Restaura un perfil oficial. Los manifiestos anteriores solo se continúan con Reanudar.')
        if not self.txt_salida.text().strip():
            raise ValueError('Indica una carpeta de salida nueva.')
        raiz = Path(self.txt_salida.text()).resolve()
        if raiz.exists():
            raise ValueError('La carpeta ya existe. Usa Reanudar o elige una carpeta nueva.')
        nombres = [self.perfil.ambiente.currentData() if not self.perfil.personalizado else 'personalizado']
        trabajos = []
        for nombre in nombres:
            config = seleccion.copy()
            for clave in ('mapas', 'poblaciones', 'algoritmos', 'semillas'):
                config[clave] = seleccion[clave].copy()
            if 'genetico' in config['algoritmos']:
                ruta = self.txt_politica.text().strip()
                validar_politica(ruta, config['semillas'])
                config['politica_genetica'] = str(Path(ruta).resolve())
            else:
                config.pop('politica_genetica', None)
            config, _ = preparar_configuracion(config)
            destino = raiz / (nombre + '_' + config['modo'])
            trabajos.append({'nombre': nombre, 'config': config, 'destino': destino})
        return trabajos

    def _iniciar_benchmark(self):
        try:
            if self.estado_gui.ocupado is not None:
                raise ValueError('Ya hay un cálculo activo.')
            trabajos = self.preparar_trabajos()
            for trabajo in trabajos:
                guardar_json(trabajo['destino'] / 'configuracion_gui.json', trabajo['config'])
            self.iniciar_trabajos(trabajos)
        except (ValueError, OSError, TypeError, KeyError) as error:
            QtWidgets.QMessageBox.warning(self, 'No se inició', str(error))

    def iniciar_trabajos(self, trabajos):
        self.trabajos = trabajos
        self.cola = trabajos.copy()
        self.txt_log.clear()
        self.resultados.clear()
        for t in trabajos:
            self.resultados.addItem(t['nombre'], str(t['destino']))
        self._siguiente()

    def _siguiente(self):
        if not self.cola:
            self.timer.stop()
            self._actualizar_botones()
            return
        self.actual = self.cola.pop(0)
        self.resultados.setCurrentIndex(self.trabajos.index(self.actual))
        self.lbl_estado.setText('Ejecutando ' + self.actual['nombre'] + '. Una búsqueda puede tardar sin emitir progreso.')
        try:
            # El módulo general ejecuta exactamente la selección, sin omisiones automáticas.
            self.control.iniciar(['-m', 'src.evaluation.benchmark', '--config',
                                  str(self.actual['destino'] / 'configuracion_gui.json'),
                                  '--salida', str(self.actual['destino'])])
            self.timer.start()
            self._actualizar_progreso()
        except ValueError as error:
            self.cola.clear()
            self.lbl_estado.setText(str(error))
        self._actualizar_botones()

    def _leer_progreso(self, trabajo):
        c = trabajo['config']
        total = len(c['mapas']) * len(c['poblaciones']) * len(c['algoritmos']) * len(c['semillas'])
        destino = trabajo['destino']
        # Los checkpoints son la autoridad, incluso después de SIGTERM antes del finally.
        completas = len(list((destino / 'runs').glob('*.json')))
        return completas, total

    def _actualizar_progreso(self):
        if self.actual is None:
            return
        actual, total = self._leer_progreso(self.actual)
        self.barra_progreso.setValue(int(100 * actual / total))
        pares = [self._leer_progreso(t) for t in self.trabajos]
        self.barra_lote.setValue(int(100 * sum(p[0] for p in pares) / sum(p[1] for p in pares)))

    def _finalizado(self, codigo, cancelado):
        if self._solo_reporte:
            self._solo_reporte = False
            self.lbl_estado.setText('Reporte regenerado.' if codigo == 0 and not cancelado else 'No se completó la exportación. Revisa el registro.')
            self._actualizar_botones()
            if self._cerrar_pendiente:
                self.close()
            return
        self._actualizar_progreso()
        actual, total = self._leer_progreso(self.actual)
        if cancelado:
            self.cola.clear()
            self.lbl_estado.setText(f'Detenido. {actual}/{total} runs guardados. Puedes reanudar.')
        elif codigo != 0 or actual != total:
            self.cola.clear()
            self.lbl_estado.setText(f'Ejecución incompleta: {actual}/{total}. Código {codigo}. Revisa el registro.')
        elif self.cola:
            self._siguiente()
            return
        else:
            self.lbl_estado.setText('Lote completado. Reportes disponibles por ambiente.')
        self.timer.stop()
        self._actualizar_botones()
        # Preparar una ruta nueva para la siguiente ejecución, conservar el selector de resultados.
        self.txt_salida.setText(str(nuevo_destino(RAIZ / 'results/raw/gui', 'experimento')))
        if self._cerrar_pendiente:
            self.close()

    def _detener_benchmark(self):
        self.cola.clear()
        self.control.detener()
        self.lbl_estado.setText('Deteniendo; se conservarán los runs completos…')

    def _elegir_reanudacion(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Reanudar manifiesto', str(RAIZ / 'results/raw'), 'Manifiesto (manifiesto.json)')
        if ruta:
            try:
                self.reanudar(ruta)
            except (ValueError, OSError, KeyError, TypeError) as error:
                QtWidgets.QMessageBox.warning(self, 'No se reanudó', str(error))

    def reanudar(self, ruta):
        if self.estado_gui.ocupado is not None:
            raise ValueError('Ya hay un cálculo activo.')
        ruta = Path(ruta)
        config = json.loads(ruta.read_text())['identidad']['configuracion']
        # Validar antes de iniciar; el ejecutor verifica además las huellas originales.
        config, _ = preparar_configuracion(config)
        self.perfil.mostrar(config)
        self.txt_politica.setText(config.get('politica_genetica', ''))
        guardar_json(ruta.parent / 'configuracion_gui.json', config)
        self.iniciar_trabajos([{'nombre': ruta.parent.name, 'config': config, 'destino': ruta.parent}])

    def _agregar_log(self, linea):
        self.txt_log.appendPlainText(linea)

    def _cargar_resultados(self):
        ruta = QtWidgets.QFileDialog.getExistingDirectory(self, 'Carpeta del escenario', str(RAIZ / 'results/raw'))
        if ruta:
            self.resultados.addItem(Path(ruta).name, ruta)
            self.resultados.setCurrentIndex(self.resultados.count() - 1)

    def _ver_reporte(self):
        ruta = self.resultados.currentData()
        if not ruta:
            return
        try:
            texto = (Path(ruta) / 'reporte_benchmark.txt').read_text(encoding='utf-8')
            dialogo = QtWidgets.QDialog(self)
            dialogo.setWindowTitle('Reporte · ' + Path(ruta).name)
            dialogo.resize(1380, 750)
            layout = QtWidgets.QVBoxLayout(dialogo)
            vista = QtWidgets.QPlainTextEdit()
            vista.setReadOnly(True)
            vista.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
            vista.setFont(QtGui.QFont('monospace', 10))
            vista.setPlainText(texto)
            layout.addWidget(vista)
            dialogo.exec_()
        except OSError as error:
            QtWidgets.QMessageBox.warning(self, 'Reporte no disponible', str(error))

    def _abrir_carpeta(self):
        if self.resultados.currentData():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.resultados.currentData()))

    def _regenerar(self):
        if self.resultados.currentData():
            try:
                self._solo_reporte = True
                self.control.iniciar(['-m', 'src.evaluation.benchmark', '--solo-reporte', '--salida', self.resultados.currentData()])
                self._actualizar_botones()
            except ValueError as error:
                self._solo_reporte = False
                QtWidgets.QMessageBox.warning(self, 'No se regeneró', str(error))

    def closeEvent(self, event):
        if self.control.activo:
            respuesta = QtWidgets.QMessageBox.question(self, 'Detener y cerrar', 'Hay un proceso activo. ¿Detenerlo y cerrar cuando termine?')
            if respuesta == QtWidgets.QMessageBox.Yes:
                self._cerrar_pendiente = True
                self._detener_benchmark()
            event.ignore()
        else:
            event.accept()
