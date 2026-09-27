"""Selección de perfiles oficiales y edición explícita de copias personales."""
from copy import deepcopy
import math
from pathlib import Path
from PyQt5 import QtCore, QtWidgets
from src.simulation.motor import VALORES_INICIALES
from .experimentos import AMBIENTES, ALGORITMOS, RAIZ, cargar_perfil, leer_configuracion, guardar_copia


def enteros(texto):
    valores = [int(s) for s in texto.replace(',', ' ').split()]
    if not valores or len(set(valores)) != len(valores):
        raise ValueError('Indica enteros distintos, separados por espacios o comas.')
    return valores


class PerfilWidget(QtWidgets.QWidget):
    cambiado = QtCore.pyqtSignal()

    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado_gui = estado
        self.personalizado = False
        self._cargando = False
        layout = QtWidgets.QVBoxLayout(self)
        fila = QtWidgets.QHBoxLayout()
        self.ambiente = QtWidgets.QComboBox()
        for a in AMBIENTES:
            self.ambiente.addItem(a.capitalize(), a)
        self.ambiente.setCurrentIndex(0)
        fila.addWidget(self.ambiente)
        self.etiqueta_evaluacion = QtWidgets.QLabel('Evaluación final')
        fila.addWidget(self.etiqueta_evaluacion)
        layout.addLayout(fila)
        acciones = QtWidgets.QHBoxLayout()
        self.btn_copia = QtWidgets.QPushButton('✏️ Modificar parámetros')
        self.btn_copia.setToolTip('Habilita la edición de parámetros, semillas y poblaciones')
        self.btn_copia.clicked.connect(self.crear_copia)
        self.btn_cargar = QtWidgets.QPushButton('Cargar JSON')
        self.btn_cargar.clicked.connect(self.cargar)
        self.btn_guardar = QtWidgets.QPushButton('Guardar copia')
        self.btn_guardar.clicked.connect(self.guardar)
        self.btn_oficial = QtWidgets.QPushButton('Restaurar oficial')
        self.btn_oficial.clicked.connect(self.cargar_oficial)
        for b in (self.btn_copia, self.btn_cargar, self.btn_guardar, self.btn_oficial):
            acciones.addWidget(b)
        layout.addLayout(acciones)
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)
        seleccion = QtWidgets.QWidget()
        fila = QtWidgets.QHBoxLayout(seleccion)
        self.mapas = QtWidgets.QListWidget()
        self.poblaciones = QtWidgets.QListWidget()
        self.algoritmos = QtWidgets.QListWidget()
        for titulo, lista in [('Mapas', self.mapas), ('Personas', self.poblaciones), ('Algoritmos', self.algoritmos)]:
            caja = QtWidgets.QGroupBox(titulo)
            v = QtWidgets.QVBoxLayout(caja)
            lista.setMaximumHeight(160)
            v.addWidget(lista)
            fila.addWidget(caja)
            lista.itemChanged.connect(self._avisar)
        self.tabs.addTab(seleccion, 'Selección')
        parametros = QtWidgets.QWidget()
        forma = QtWidgets.QFormLayout(parametros)
        self.btn_habilitar_params = QtWidgets.QPushButton("✏️ Habilitar modificación de parámetros")
        self.btn_habilitar_params.clicked.connect(self.crear_copia)
        forma.addRow(self.btn_habilitar_params)
        self.inputs = {}
        nombres = {'capacidad_pasillos': 'Capacidad de pasillo', 'capacidad_salida': 'Admisiones por salida',
                   'cantidad_focos': 'Focos iniciales', 'distancia_min_salida': 'Distancia mín. fuego a salida',
                   'k': 'Fuego cada N turnos', 'probabilidad': 'Probabilidad de fuego',
                   'max_turnos': 'Máximo de turnos', 'alpha': 'Peso de congestión', 'umbral_bloqueo': 'Turnos bloqueado'}
        for clave, valor in VALORES_INICIALES.items():
            if clave in ('probabilidad', 'alpha'):
                campo = QtWidgets.QDoubleSpinBox()
                campo.setDecimals(4)
                campo.setRange(0, 1 if clave == 'probabilidad' else 10000)
            else:
                campo = QtWidgets.QSpinBox()
                campo.setRange(0 if clave in ('cantidad_focos', 'distancia_min_salida') else 1, 1000000)
            campo.valueChanged.connect(self._avisar)
            self.inputs[clave] = campo
            forma.addRow(nombres.get(clave, clave), campo)
        self.tabs.addTab(parametros, 'Parámetros')
        datos = QtWidgets.QWidget()
        forma = QtWidgets.QFormLayout(datos)
        self.semillas = QtWidgets.QPlainTextEdit()
        self.semillas.setMaximumHeight(85)
        self.semillas.textChanged.connect(self._avisar)
        self.poblaciones_texto = QtWidgets.QLineEdit()
        self.btn_poblaciones = QtWidgets.QPushButton('Aplicar poblaciones')
        self.btn_poblaciones.clicked.connect(self._cambiar_poblaciones)
        self.btn_mapa = QtWidgets.QPushButton('Agregar mapa TXT')
        self.btn_mapa.clicked.connect(self._agregar_mapa)
        forma.addRow('Semillas explícitas', self.semillas)
        forma.addRow('Personas por escenario', self.poblaciones_texto)
        forma.addRow(self.btn_poblaciones, self.btn_mapa)
        self.tabs.addTab(datos, 'Semillas y copia')
        self.resumen = QtWidgets.QLabel()
        self.resumen.setWordWrap(True)
        layout.addWidget(self.resumen)
        self.ambiente.currentIndexChanged.connect(self.cargar_oficial)
        self.estado_gui.ambiente_cambiado.connect(self._ambiente_externo)
        self.ambiente.setCurrentIndex(self.ambiente.findData(estado.ambiente))
        self.cargar_oficial()

    def _ambiente_externo(self, nombre):
        if not self.personalizado and self.isEnabled():
            self.ambiente.setCurrentIndex(self.ambiente.findData(nombre))

    def _llenar(self, lista, valores, seleccionados):
        lista.clear()
        for valor in valores:
            texto = Path(valor).name if lista is self.mapas else str(valor)
            item = QtWidgets.QListWidgetItem(texto)
            item.setData(QtCore.Qt.UserRole, valor)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if valor in seleccionados else QtCore.Qt.Unchecked)
            lista.addItem(item)

    def seleccion(self, lista):
        return [lista.item(i).data(QtCore.Qt.UserRole) for i in range(lista.count())
                if lista.item(i).checkState() == QtCore.Qt.Checked]

    def cargar_oficial(self, *args):
        self.personalizado = False
        self.mostrar(cargar_perfil(self.ambiente.currentData()), False)
        self.estado_gui.elegir_ambiente(self.ambiente.currentData())

    def mostrar(self, config, personalizado=True):
        if not isinstance(config, dict) or config.get('modo') not in ('piloto', 'final'):
            raise ValueError('Configuración experimental inválida.')
        for clave in ('mapas', 'poblaciones', 'algoritmos', 'semillas'):
            if not isinstance(config.get(clave), list) or not config[clave]:
                raise ValueError('Lista requerida: ' + clave)
        if any(type(n) is not int or n <= 0 for n in config['poblaciones']):
            raise ValueError('Poblaciones inválidas.')
        if any(type(n) is not int for n in config['semillas']):
            raise ValueError('Semillas inválidas.')
        if any(a not in ALGORITMOS for a in config['algoritmos']):
            raise ValueError('Algoritmo desconocido.')
        for clave, valor in config.get('parametros', {}).items():
            if clave not in self.inputs or not isinstance(valor, (int, float)) or not math.isfinite(valor):
                raise ValueError('Parámetro inválido: ' + clave)
            campo = self.inputs[clave]
            if not campo.minimum() <= valor <= campo.maximum():
                raise ValueError('Parámetro fuera de rango: ' + clave)
            if isinstance(campo, QtWidgets.QSpinBox) and type(valor) is not int:
                raise ValueError('Se requiere entero: ' + clave)
        self._cargando = True
        self.base = deepcopy(config)
        self.personalizado = personalizado
        self._llenar(self.mapas, config['mapas'], config['mapas'])
        self._llenar(self.poblaciones, config['poblaciones'], config['poblaciones'])
        self._llenar(self.algoritmos, ALGORITMOS, config['algoritmos'])
        for clave, campo in self.inputs.items():
            campo.setValue(config.get('parametros', {}).get(clave, VALORES_INICIALES[clave]))
        self.semillas.setPlainText(' '.join(map(str, config['semillas'])))
        self.poblaciones_texto.setText(', '.join(map(str, config['poblaciones'])))
        self._habilitar_copia()
        self._cargando = False
        self._avisar()

    def _habilitar_copia(self):
        for campo in [*self.inputs.values(), self.semillas, self.poblaciones_texto,
                      self.btn_poblaciones, self.btn_mapa]:
            campo.setEnabled(self.personalizado)
        self.ambiente.setEnabled(not self.personalizado)
        if hasattr(self, 'btn_habilitar_params'):
            if self.personalizado:
                self.btn_habilitar_params.setText("✓ Edición de parámetros activa (Modo personalizado)")
                self.btn_habilitar_params.setEnabled(False)
            else:
                self.btn_habilitar_params.setText("✏️ Habilitar modificación de parámetros")
                self.btn_habilitar_params.setEnabled(True)

    def crear_copia(self):
        self.personalizado = True
        self._habilitar_copia()
        self._avisar()

    def configuracion(self):
        config = deepcopy(self.base)
        config.update(mapas=self.seleccion(self.mapas), poblaciones=self.seleccion(self.poblaciones),
                      algoritmos=self.seleccion(self.algoritmos), semillas=enteros(self.semillas.toPlainText()),
                      parametros={k: c.value() for k, c in self.inputs.items()})
        if any(not config[k] for k in ('mapas', 'poblaciones', 'algoritmos')):
            raise ValueError('Selecciona al menos un mapa, población y algoritmo.')
        if any(n <= 0 for n in config['poblaciones']):
            raise ValueError('Las poblaciones deben ser positivas.')
        if config['modo'] == 'final' and len(config['semillas']) < 80:
            raise ValueError('La evaluación final requiere al menos 80 semillas distintas.')
        return config

    def _avisar(self, *args):
        if self._cargando:
            return
        try:
            c = self.configuracion()
            self.etiqueta_evaluacion.setText(f"Evaluación final · {len(c['semillas'])} repeticiones")
            n = len(c['mapas']) * len(c['poblaciones']) * len(c['semillas']) * len(c['algoritmos'])
            subconjunto = any(set(c[k]) < set(self.base[k]) for k in ('mapas', 'poblaciones', 'algoritmos'))
            tipo = 'Personalizado' if self.personalizado else 'Oficial · subconjunto' if subconjunto else 'Oficial completo'
            p = c['parametros']
            conteo = f"{n:,} simulaciones".replace(',', '.')
            if c['modo'] != 'final':
                tipo = 'Configuración histórica · solo reanudación'
            dist_txt = f" | dist. mín.: {p['distancia_min_salida']}" if p.get('distancia_min_salida', 0) > 0 else ""
            self.resumen.setText(f"{tipo} | {conteo}\n"
                f"Personas: {c['poblaciones']} | {len(c['semillas'])} semillas | Algoritmos: {', '.join(c['algoritmos'])}\n"
                f"Focos: {p['cantidad_focos']} | p={p['probabilidad']} | k={p['k']}{dist_txt} | máximo: {p['max_turnos']} turnos")
        except (ValueError, KeyError) as error:
            self.resumen.setText(str(error))
        self.cambiado.emit()

    def _cambiar_poblaciones(self):
        try:
            valores = enteros(self.poblaciones_texto.text())
            if min(valores) <= 0:
                raise ValueError('Las poblaciones deben ser positivas.')
            self._llenar(self.poblaciones, valores, valores)
            self._avisar()
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, 'Poblaciones', str(error))

    def _agregar_mapa(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Mapa', str(RAIZ / 'maps'), 'Mapas (*.txt)')
        if ruta:
            valores = [self.mapas.item(i).data(QtCore.Qt.UserRole) for i in range(self.mapas.count())]
            if ruta not in valores:
                valores.append(ruta)
                self._llenar(self.mapas, valores, valores)

    def cargar(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Configuración', str(RAIZ / 'configs'), 'JSON (*.json)')
        if ruta:
            try:
                self.mostrar(leer_configuracion(ruta))
            except (ValueError, KeyError, TypeError, OSError) as error:
                QtWidgets.QMessageBox.warning(self, 'Configuración inválida', str(error))

    def guardar(self):
        ruta, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Guardar copia', str(RAIZ / 'results/configuraciones/copia.json'), 'JSON (*.json)')
        if ruta:
            try:
                guardar_copia(ruta, self.configuracion())
            except (ValueError, OSError) as error:
                QtWidgets.QMessageBox.warning(self, 'No se guardó', str(error))
