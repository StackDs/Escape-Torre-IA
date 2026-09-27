"""Vista principal de simulación interactiva con panel de control izquierdo, visualizador de mapa y métricas."""

import random
from copy import deepcopy
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets

from src.algorithms.Genetic.politica import obtener_politica_genetica
from src.gui.benchmark_dialog import BenchmarkDialog
from src.gui.map_canvas import MapCanvas
from src.gui.training_dialog import TrainingDialog
from src.gui.experimentos import estado_compartido, cargar_perfil, validar_politica, AMBIENTES
from src.models.agente import State
from src.models.mapa import cargar_mapa
from src.simulation.motor import MotorSimulacion, VALORES_INICIALES

RAIZ = Path(__file__).resolve().parents[2]

ALGORITMOS = [
    ("bfs", "BFS (Anchura)"),
    ("dfs", "DFS (Profundidad)"),
    ("ucs", "UCS (Costo Uniforme)"),
    ("a_star", "A* (A-Estrella)"),
    ("greedy", "Greedy (Voraz)"),
    ("ida_star", "IDA* (Iterativo)"),
    ("genetico", "Algoritmo Genético"),
]

MAPAS_PREDETERMINADOS = [
    ("maps/bottleneck.txt", "Cuello de Botella"),
    ("maps/corporate_maze.txt", "Laberinto Corporativo"),
    ("maps/open_area.txt", "Área Abierta"),
]


class TrabajoSimulacion(QtCore.QThread):
    """Trabaja sobre una copia: la vista conserva un mapa estable hasta terminar."""
    def __init__(self, motor, completa, parent=None):
        super().__init__(parent)
        self.motor = deepcopy(motor)
        self.completa = completa
        self.error = None

    def run(self):
        try:
            while not self.motor.terminada and not self.isInterruptionRequested():
                self.motor.avanzar_turno()
                if not self.completa:
                    break
        except Exception as error:
            self.error = str(error)


class SimulationView(QtWidgets.QWidget):
    """Panel principal de simulación individual y control de parámetros."""

    volver_inicio_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.motor = None
        self.estado_gui = estado_compartido(parent)
        self._trabajador = None
        self._aplicando_perfil = False
        self.max_turnos = 1000
        self.timer_animacion = QtCore.QTimer(self)
        self.timer_animacion.timeout.connect(self._paso_animacion)

        # Política genética cargada
        self.ruta_politica_genetica = Path(self.estado_gui.politica) if self.estado_gui.politica else RAIZ / "results/policies/mejor.json"
        self.politica_genetica_obj = None
        self.es_politica_entrenada = False

        self._init_ui()
        self._cargar_politica_actual()
        self.estado_gui.ambiente_cambiado.connect(self.aplicar_ambiente)
        self.estado_gui.politica_cambiada.connect(self._politica_compartida)
        self.aplicar_ambiente(self.estado_gui.ambiente)

    def _init_ui(self):
        layout_principal = QtWidgets.QVBoxLayout(self)
        layout_principal.setContentsMargins(8, 6, 8, 6)
        layout_principal.setSpacing(6)

        # Barra superior con navegación y títulos
        barra_superior = QtWidgets.QHBoxLayout()
        btn_volver = QtWidgets.QPushButton("← Volver al Inicio")
        self.btn_volver = btn_volver
        btn_volver.setProperty("variant", "secondary")
        btn_volver.clicked.connect(self._al_volver_inicio)
        barra_superior.addWidget(btn_volver)

        self.btn_bench = QtWidgets.QPushButton("📊 Benchmark")
        self.btn_bench.setProperty("variant", "secondary")
        self.btn_bench.setToolTip("Abrir ventana de benchmark comparativo")
        self.btn_bench.clicked.connect(self._abrir_benchmark)
        barra_superior.addWidget(self.btn_bench)

        self.lbl_titulo_vista = QtWidgets.QLabel("Simulador de Evacuación de Emergencia")
        self.lbl_titulo_vista.setStyleSheet("font-size: 15px; font-weight: bold; color: #f8fafc;")
        barra_superior.addWidget(self.lbl_titulo_vista)

        barra_superior.addStretch()

        self.badge_algo = QtWidgets.QLabel("A*")
        self.badge_algo.setProperty("badge", "true")
        barra_superior.addWidget(self.badge_algo)

        self.badge_mapa = QtWidgets.QLabel("Cuello de Botella")
        self.badge_mapa.setProperty("badge", "true")
        barra_superior.addWidget(self.badge_mapa)

        self.lbl_turno = QtWidgets.QLabel("Turno: 0")
        self.lbl_turno.setStyleSheet("font-weight: bold; color: #38bdf8;")
        barra_superior.addWidget(self.lbl_turno)

        layout_principal.addLayout(barra_superior)

        # Zona central: Splitter horizontal (Panel Izquierdo | Mapa Central | Métricas Derecha)
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # 1. Panel Lateral Izquierdo (Pestañas de Parámetros + Acciones fijas en la base)
        panel_izq = QtWidgets.QWidget()
        panel_izq.setMinimumWidth(360)
        panel_izq.setMaximumWidth(420)
        layout_izq = QtWidgets.QVBoxLayout(panel_izq)
        layout_izq.setContentsMargins(6, 4, 6, 6)
        layout_izq.setSpacing(10)

        # QTabWidget para organizar los parámetros en 2 pestañas temáticas
        self.tabs_parametros = QtWidgets.QTabWidget()
        self.tabs_parametros.setUsesScrollButtons(False)
        self.tabs_parametros.tabBar().setExpanding(False)

        # ==========================================
        # PESTAÑA 1: 🏢 Escenario y Agentes
        # ==========================================
        self.scroll_tab1 = QtWidgets.QScrollArea()
        self.scroll_tab1.setWidgetResizable(True)
        self.scroll_tab1.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_tab1.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_tab1.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        widget_tab1 = QtWidgets.QWidget()
        lay_tab1 = QtWidgets.QVBoxLayout(widget_tab1)
        lay_tab1.setContentsMargins(8, 8, 8, 8)
        lay_tab1.setSpacing(11)

        # Grupo: Algoritmo de Búsqueda
        grp_algo = QtWidgets.QGroupBox("Algoritmo de Búsqueda")
        lay_algo = QtWidgets.QVBoxLayout(grp_algo)
        lay_algo.setContentsMargins(10, 10, 10, 10)
        lay_algo.setSpacing(10)
        self.combo_algo = QtWidgets.QComboBox()
        for cod, nom in ALGORITMOS:
            self.combo_algo.addItem(nom, cod)
        self.combo_algo.currentIndexChanged.connect(self._al_cambiar_algoritmo)
        lay_algo.addWidget(self.combo_algo)

        # Sub-panel de opciones para Algoritmo Genético
        self.panel_genetico = QtWidgets.QFrame()
        self.panel_genetico.setObjectName("panelGenetico")
        self.panel_genetico.setStyleSheet("#panelGenetico { background-color: #0f172a; border-radius: 6px; }")
        lay_gen = QtWidgets.QVBoxLayout(self.panel_genetico)
        lay_gen.setContentsMargins(8, 8, 8, 8)
        lay_gen.setSpacing(10)

        self.lbl_estado_genetico = QtWidgets.QLabel("Estado: No entrenado (Pesos por defecto)")
        self.lbl_estado_genetico.setStyleSheet("font-size: 11px; color: #f59e0b;")
        self.lbl_estado_genetico.setWordWrap(True)
        lay_gen.addWidget(self.lbl_estado_genetico)

        fila_btn_gen = QtWidgets.QHBoxLayout()
        fila_btn_gen.setSpacing(6)
        self.btn_cargar_pol = QtWidgets.QPushButton("📂 Cargar...")
        self.btn_cargar_pol.setProperty("variant", "secondary")
        self.btn_cargar_pol.clicked.connect(self._examinar_politica)
        fila_btn_gen.addWidget(self.btn_cargar_pol)

        self.btn_entrenar_pol = QtWidgets.QPushButton("🧬 Entrenar...")
        self.btn_entrenar_pol.setProperty("variant", "secondary")
        self.btn_entrenar_pol.clicked.connect(self._abrir_entrenamiento)
        fila_btn_gen.addWidget(self.btn_entrenar_pol)
        lay_gen.addLayout(fila_btn_gen)

        self.lbl_pesos_genetico = QtWidgets.QLabel("Pesos: Congestión=1.0 | Riesgo=2.0 | Umbral=3")
        self.lbl_pesos_genetico.setStyleSheet("font-size: 10px; color: #94a3b8;")
        lay_gen.addWidget(self.lbl_pesos_genetico)

        lay_algo.addWidget(self.panel_genetico)
        self.panel_genetico.setVisible(False)
        lay_tab1.addWidget(grp_algo)

        # Grupo: Mapa y Población
        grp_mapa = QtWidgets.QGroupBox("Mapa y Población")
        lay_mapa = QtWidgets.QGridLayout(grp_mapa)
        lay_mapa.setContentsMargins(10, 10, 10, 10)
        lay_mapa.setVerticalSpacing(10)
        lay_mapa.setHorizontalSpacing(8)

        # Fila 0: Mapa y botón examinar
        lay_mapa.addWidget(QtWidgets.QLabel("Mapa:"), 0, 0)
        fila_mapa = QtWidgets.QHBoxLayout()
        fila_mapa.setSpacing(6)
        self.combo_mapa = QtWidgets.QComboBox()
        self.combo_mapa.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo_mapa.setMinimumContentsLength(8)
        for rel_path, nom in MAPAS_PREDETERMINADOS:
            self.combo_mapa.addItem(nom, str((RAIZ / rel_path).resolve()))
        self.combo_mapa.currentIndexChanged.connect(self._al_cambiar_mapa)
        fila_mapa.addWidget(self.combo_mapa, 1)

        self.btn_examinar_mapa = QtWidgets.QPushButton("Examinar...")
        self.btn_examinar_mapa.setProperty("variant", "secondary")
        self.btn_examinar_mapa.setMinimumWidth(96)
        self.btn_examinar_mapa.clicked.connect(self._examinar_mapa)
        fila_mapa.addWidget(self.btn_examinar_mapa)
        lay_mapa.addLayout(fila_mapa, 0, 1, 1, 3)

        # Fila 1: Población inicial
        lay_mapa.addWidget(QtWidgets.QLabel("Población:"), 1, 0)
        self.spin_poblacion = QtWidgets.QSpinBox()
        self.spin_poblacion.setRange(1, 1000)
        self.spin_poblacion.setValue(20)
        lay_mapa.addWidget(self.spin_poblacion, 1, 1, 1, 3)

        # Fila 2: Pasillos y Salida juntos (2 columnas compactas)
        lay_mapa.addWidget(QtWidgets.QLabel("Pasillos:"), 2, 0)
        self.spin_cap_pasillos = QtWidgets.QSpinBox()
        self.spin_cap_pasillos.setRange(1, 20)
        self.spin_cap_pasillos.setValue(VALORES_INICIALES["capacidad_pasillos"])
        lay_mapa.addWidget(self.spin_cap_pasillos, 2, 1)

        lay_mapa.addWidget(QtWidgets.QLabel("Salida:"), 2, 2)
        self.spin_cap_salida = QtWidgets.QSpinBox()
        self.spin_cap_salida.setRange(1, 20)
        self.spin_cap_salida.setValue(VALORES_INICIALES["capacidad_salida"])
        lay_mapa.addWidget(self.spin_cap_salida, 2, 3)

        lay_tab1.addWidget(grp_mapa)
        lay_tab1.addStretch()
        self.scroll_tab1.setWidget(widget_tab1)

        # ==========================================
        # PESTAÑA 2: 🔥 Fuego y Búsqueda
        # ==========================================
        self.scroll_tab2 = QtWidgets.QScrollArea()
        self.scroll_tab2.setWidgetResizable(True)
        self.scroll_tab2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_tab2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_tab2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        widget_tab2 = QtWidgets.QWidget()
        lay_tab2 = QtWidgets.QVBoxLayout(widget_tab2)
        lay_tab2.setContentsMargins(8, 8, 8, 8)
        lay_tab2.setSpacing(11)

        # Grupo: Propagación de Fuego
        grp_fuego = QtWidgets.QGroupBox("Propagación de Fuego")
        lay_fuego = QtWidgets.QGridLayout(grp_fuego)
        lay_fuego.setContentsMargins(10, 10, 10, 10)
        lay_fuego.setVerticalSpacing(10)
        lay_fuego.setHorizontalSpacing(8)

        # Fila 0: Focos y Frecuencia k juntos
        lay_fuego.addWidget(QtWidgets.QLabel("Focos:"), 0, 0)
        self.spin_focos = QtWidgets.QSpinBox()
        self.spin_focos.setRange(0, 50)
        self.spin_focos.setValue(VALORES_INICIALES["cantidad_focos"])
        lay_fuego.addWidget(self.spin_focos, 0, 1)

        lay_fuego.addWidget(QtWidgets.QLabel("Intervalo k:"), 0, 2)
        self.spin_k = QtWidgets.QSpinBox()
        self.spin_k.setRange(1, 50)
        self.spin_k.setValue(VALORES_INICIALES["k"])
        lay_fuego.addWidget(self.spin_k, 0, 3)

        # Fila 1: Probabilidad y Distancia mínima a salida
        lay_fuego.addWidget(QtWidgets.QLabel("Probabilidad:"), 1, 0)
        self.spin_prob_fuego = QtWidgets.QDoubleSpinBox()
        self.spin_prob_fuego.setRange(0.0, 1.0)
        self.spin_prob_fuego.setSingleStep(0.05)
        self.spin_prob_fuego.setValue(VALORES_INICIALES["probabilidad"])
        lay_fuego.addWidget(self.spin_prob_fuego, 1, 1)

        lay_fuego.addWidget(QtWidgets.QLabel("Dist. mín. salida:"), 1, 2)
        self.spin_dist_salida = QtWidgets.QSpinBox()
        self.spin_dist_salida.setRange(0, 100)
        self.spin_dist_salida.setValue(VALORES_INICIALES.get("distancia_min_salida", 0))
        lay_fuego.addWidget(self.spin_dist_salida, 1, 3)

        lay_tab2.addWidget(grp_fuego)

        # Grupo: Búsqueda y Azar
        grp_busq = QtWidgets.QGroupBox("Búsqueda y Azar")
        lay_busq = QtWidgets.QGridLayout(grp_busq)
        lay_busq.setContentsMargins(10, 10, 10, 10)
        lay_busq.setVerticalSpacing(10)
        lay_busq.setHorizontalSpacing(8)

        # Fila 0: Alpha y Umbral juntos
        lay_busq.addWidget(QtWidgets.QLabel("Alpha:"), 0, 0)
        self.spin_alpha = QtWidgets.QDoubleSpinBox()
        self.spin_alpha.setRange(0.0, 10.0)
        self.spin_alpha.setSingleStep(0.1)
        self.spin_alpha.setValue(VALORES_INICIALES["alpha"])
        lay_busq.addWidget(self.spin_alpha, 0, 1)

        lay_busq.addWidget(QtWidgets.QLabel("Umbral:"), 0, 2)
        self.spin_umbral = QtWidgets.QSpinBox()
        self.spin_umbral.setRange(1, 20)
        self.spin_umbral.setValue(VALORES_INICIALES["umbral_bloqueo"])
        lay_busq.addWidget(self.spin_umbral, 0, 3)

        # Fila 1: Máximo de Turnos
        lay_busq.addWidget(QtWidgets.QLabel("Máx. Turnos:"), 1, 0)
        self.spin_max_turnos = QtWidgets.QSpinBox()
        self.spin_max_turnos.setRange(10, 50000)
        self.spin_max_turnos.setSingleStep(50)
        self.spin_max_turnos.setValue(self.max_turnos)
        lay_busq.addWidget(self.spin_max_turnos, 1, 1, 1, 3)

        # Fila 2: Semilla y botón aleatorio juntos
        lay_busq.addWidget(QtWidgets.QLabel("Semilla:"), 2, 0)
        fila_sem = QtWidgets.QHBoxLayout()
        fila_sem.setSpacing(6)
        self.spin_semilla = QtWidgets.QSpinBox()
        self.spin_semilla.setRange(0, 999999999)
        self.spin_semilla.setValue(100)
        fila_sem.addWidget(self.spin_semilla, 1)

        self.btn_azar_sem = QtWidgets.QPushButton("🎲")
        self.btn_azar_sem.setProperty("variant", "secondary")
        self.btn_azar_sem.setToolTip("Generar semilla aleatoria")
        self.btn_azar_sem.setFixedWidth(38)
        self.btn_azar_sem.clicked.connect(self._generar_semilla_aleatoria)
        fila_sem.addWidget(self.btn_azar_sem)
        lay_busq.addLayout(fila_sem, 2, 1, 1, 3)

        lay_tab2.addWidget(grp_busq)
        lay_tab2.addStretch()
        self.scroll_tab2.setWidget(widget_tab2)

        # Agregar pestañas
        self.tabs_parametros.addTab(self.scroll_tab1, "🏢 Escenario y Agentes")
        self.tabs_parametros.addTab(self.scroll_tab2, "🔥 Fuego y Búsqueda")
        layout_izq.addWidget(self.tabs_parametros, 1)

        # Compatibilidad hacia atrás
        self.scroll_izq = self.scroll_tab1

        # Conectar cambios de parámetros en vivo
        for spin in (
            self.spin_poblacion,
            self.spin_cap_pasillos,
            self.spin_cap_salida,
            self.spin_focos,
            self.spin_dist_salida,
            self.spin_k,
            self.spin_prob_fuego,
            self.spin_alpha,
            self.spin_umbral,
            self.spin_max_turnos,
            self.spin_semilla,
        ):
            spin.valueChanged.connect(self._al_cambiar_parametro)

        # ==========================================
        # ZONA DE ACCIONES FIJA EN LA BASE
        # ==========================================
        grp_ctrl = QtWidgets.QGroupBox("Acciones de Simulación")
        lay_ctrl = QtWidgets.QVBoxLayout(grp_ctrl)
        lay_ctrl.setContentsMargins(10, 10, 10, 10)
        lay_ctrl.setSpacing(10)

        self.btn_ejecutar_completa = QtWidgets.QPushButton("▶ Ejecutar Simulación Completa")
        self.btn_ejecutar_completa.setProperty("variant", "success")
        self.btn_ejecutar_completa.clicked.connect(self.ejecutar_simulacion_completa)
        lay_ctrl.addWidget(self.btn_ejecutar_completa)

        fila_pasos = QtWidgets.QHBoxLayout()
        fila_pasos.setSpacing(6)
        self.btn_animar = QtWidgets.QPushButton("⏯ Animar / Pausa")
        self.btn_animar.clicked.connect(self.alternar_animacion)
        fila_pasos.addWidget(self.btn_animar)

        self.btn_paso = QtWidgets.QPushButton("⏭ +1 Turno")
        self.btn_paso.setProperty("variant", "secondary")
        self.btn_paso.clicked.connect(self.avanzar_un_paso)
        fila_pasos.addWidget(self.btn_paso)
        lay_ctrl.addLayout(fila_pasos)

        fila_reinicios = QtWidgets.QHBoxLayout()
        fila_reinicios.setSpacing(6)
        self.btn_reiniciar = QtWidgets.QPushButton("🔄 Reiniciar")
        self.btn_reiniciar.setProperty("variant", "secondary")
        self.btn_reiniciar.setToolTip("Reinicia la simulación al turno 0 conservando los parámetros actuales")
        self.btn_reiniciar.clicked.connect(self.reiniciar_simulacion)
        fila_reinicios.addWidget(self.btn_reiniciar)

        self.btn_restablecer = QtWidgets.QPushButton("↺ Restablecer")
        self.btn_restablecer.setProperty("variant", "secondary")
        self.btn_restablecer.setToolTip("Restaura todos los parámetros a sus valores por defecto y reinicia al turno 0")
        self.btn_restablecer.clicked.connect(self.restablecer_parametros)
        fila_reinicios.addWidget(self.btn_restablecer)
        lay_ctrl.addLayout(fila_reinicios)

        # Velocidad de animación
        fila_vel = QtWidgets.QHBoxLayout()
        fila_vel.setSpacing(6)
        fila_vel.addWidget(QtWidgets.QLabel("Velocidad:"))
        self.slider_velocidad = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_velocidad.setRange(10, 300)
        self.slider_velocidad.setValue(60)
        self.slider_velocidad.setToolTip("Intervalo entre turnos (ms) - menor es más rápido")
        fila_vel.addWidget(self.slider_velocidad, 1)

        self.lbl_velocidad = QtWidgets.QLabel("60 ms (~17 t/s)")
        self.lbl_velocidad.setStyleSheet("font-size: 11px; color: #38bdf8; font-weight: bold;")
        self.lbl_velocidad.setMinimumWidth(85)
        fila_vel.addWidget(self.lbl_velocidad)
        self.slider_velocidad.valueChanged.connect(self._al_cambiar_velocidad)
        self._al_cambiar_velocidad(self.slider_velocidad.value())
        lay_ctrl.addLayout(fila_vel)

        layout_izq.addWidget(grp_ctrl, 0)

        # Lista de controles de parámetros para bloqueo durante simulación
        self.controles_parametros = [
            self.combo_algo,
            self.combo_mapa,
            self.btn_examinar_mapa,
            self.spin_poblacion,
            self.spin_cap_pasillos,
            self.spin_cap_salida,
            self.spin_focos,
            self.spin_dist_salida,
            self.spin_k,
            self.spin_prob_fuego,
            self.spin_alpha,
            self.spin_umbral,
            self.spin_semilla,
            self.btn_azar_sem,
            self.btn_cargar_pol,
            self.btn_entrenar_pol,
        ]

        splitter.addWidget(panel_izq)

        # 2. Visualizador Central del Mapa
        widget_centro = QtWidgets.QWidget()
        layout_centro = QtWidgets.QVBoxLayout(widget_centro)
        layout_centro.setContentsMargins(0, 0, 0, 0)
        layout_centro.setSpacing(6)

        self.canvas = MapCanvas()
        layout_centro.addWidget(self.canvas, 1)

        # Barra de leyenda y botones de zoom
        barra_leyenda = QtWidgets.QHBoxLayout()
        barra_leyenda.setContentsMargins(2, 2, 2, 2)
        btn_ajustar_zoom = QtWidgets.QPushButton("🔍")
        btn_ajustar_zoom.setProperty("variant", "secondary")
        btn_ajustar_zoom.setToolTip("Ajustar visualización al tamaño de la ventana")
        btn_ajustar_zoom.setFixedWidth(34)
        btn_ajustar_zoom.clicked.connect(self.canvas.ajustar_a_vista)
        barra_leyenda.addWidget(btn_ajustar_zoom)

        barra_leyenda.addStretch()

        leyendas = [
            ("█ Muro", "#181f2f"),
            ("█ Pasillo", "#334155"),
            ("█ Salida", "#10b981"),
            ("🔥 Fuego", "#ef4444"),
            ("● Agente", "#38bdf8"),
            ("✖ Fallecido", "#7f1d1d"),
        ]
        for texto, color in leyendas:
            lbl = QtWidgets.QLabel(texto)
            lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10px; margin-left: 2px;")
            barra_leyenda.addWidget(lbl)

        layout_centro.addLayout(barra_leyenda)
        splitter.addWidget(widget_centro)

        # 3. Panel Lateral Derecho: Métricas y Estadísticas
        widget_der = QtWidgets.QWidget()
        widget_der.setMinimumWidth(260)
        widget_der.setMaximumWidth(320)
        layout_der = QtWidgets.QVBoxLayout(widget_der)
        layout_der.setContentsMargins(10, 5, 5, 5)
        layout_der.setSpacing(10)

        lbl_metricas_tit = QtWidgets.QLabel("Métricas y Resultados")
        lbl_metricas_tit.setProperty("heading", "true")
        layout_der.addWidget(lbl_metricas_tit)

        # Tarjeta: Supervivencia
        card_sup = QtWidgets.QFrame()
        card_sup.setObjectName("cardSup")
        card_sup.setStyleSheet("#cardSup { background-color: #1e293b; border-radius: 8px; }")
        lay_sup = QtWidgets.QVBoxLayout(card_sup)
        lay_sup.setContentsMargins(8, 6, 8, 6)
        lay_sup.setSpacing(3)
        lay_sup.addWidget(QtWidgets.QLabel("Supervivencia:"))
        self.lbl_supervivencia = QtWidgets.QLabel("0.0%")
        self.lbl_supervivencia.setStyleSheet("font-size: 26px; font-weight: 800; color: #10b981;")
        lay_sup.addWidget(self.lbl_supervivencia)
        self.barra_supervivencia = QtWidgets.QProgressBar()
        self.barra_supervivencia.setRange(0, 100)
        self.barra_supervivencia.setValue(0)
        lay_sup.addWidget(self.barra_supervivencia)
        layout_der.addWidget(card_sup)

        # Detalle de población
        grp_detalles = QtWidgets.QGroupBox("Balance de Evacuación")
        lay_det = QtWidgets.QGridLayout(grp_detalles)
        lay_det.setSpacing(8)

        lay_det.addWidget(QtWidgets.QLabel("Evacuados:"), 0, 0)
        self.val_evacuados = QtWidgets.QLabel("0")
        self.val_evacuados.setStyleSheet("color: #10b981; font-weight: bold;")
        lay_det.addWidget(self.val_evacuados, 0, 1)

        lay_det.addWidget(QtWidgets.QLabel("Fallecidos:"), 1, 0)
        self.val_fallecidos = QtWidgets.QLabel("0")
        self.val_fallecidos.setStyleSheet("color: #ef4444; font-weight: bold;")
        lay_det.addWidget(self.val_fallecidos, 1, 1)

        lay_det.addWidget(QtWidgets.QLabel("Pendientes:"), 2, 0)
        self.val_pendientes = QtWidgets.QLabel("0")
        self.val_pendientes.setStyleSheet("color: #38bdf8; font-weight: bold;")
        lay_det.addWidget(self.val_pendientes, 2, 1)

        lay_det.addWidget(QtWidgets.QLabel("Turno último evacuado:"), 3, 0)
        self.val_ultimo = QtWidgets.QLabel("N/D")
        lay_det.addWidget(self.val_ultimo, 3, 1)

        lay_det.addWidget(QtWidgets.QLabel("Motivo término:"), 4, 0)
        self.val_motivo = QtWidgets.QLabel("En curso")
        self.val_motivo.setStyleSheet("color: #94a3b8; font-style: italic;")
        lay_det.addWidget(self.val_motivo, 4, 1)

        layout_der.addWidget(grp_detalles)

        # Actividad del Motor
        grp_act = QtWidgets.QGroupBox("Actividad de Agentes")
        lay_act = QtWidgets.QGridLayout(grp_act)
        lay_act.setSpacing(8)

        lay_act.addWidget(QtWidgets.QLabel("Movimientos:"), 0, 0)
        self.val_movimientos = QtWidgets.QLabel("0")
        lay_act.addWidget(self.val_movimientos, 0, 1)

        lay_act.addWidget(QtWidgets.QLabel("Esperas / Bloqueos:"), 1, 0)
        self.val_esperas = QtWidgets.QLabel("0")
        lay_act.addWidget(self.val_esperas, 1, 1)

        lay_act.addWidget(QtWidgets.QLabel("Replanificaciones:"), 2, 0)
        self.val_planificaciones = QtWidgets.QLabel("0")
        lay_act.addWidget(self.val_planificaciones, 2, 1)

        layout_der.addWidget(grp_act)

        # Log de eventos de simulación
        grp_eventos = QtWidgets.QGroupBox("Registro de Eventos")
        lay_ev = QtWidgets.QVBoxLayout(grp_eventos)
        self.txt_eventos = QtWidgets.QPlainTextEdit()
        self.txt_eventos.setReadOnly(True)
        self.txt_eventos.setMaximumHeight(150)
        lay_ev.addWidget(self.txt_eventos)
        layout_der.addWidget(grp_eventos)

        layout_der.addStretch()
        splitter.addWidget(widget_der)

        # Proporciones de splitter
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([360, 720, 280])

        layout_principal.addWidget(splitter, 1)
        perfiles = QtWidgets.QHBoxLayout()
        self.combo_ambiente = QtWidgets.QComboBox()
        for nombre in AMBIENTES:
            self.combo_ambiente.addItem(nombre.capitalize(), nombre)
        self.combo_ambiente.setCurrentIndex(self.combo_ambiente.findData(self.estado_gui.ambiente))
        self.combo_ambiente.currentIndexChanged.connect(lambda: self.aplicar_ambiente(self.combo_ambiente.currentData()))
        self.combo_semilla_evaluacion = QtWidgets.QComboBox()
        self.combo_semilla_evaluacion.currentIndexChanged.connect(self._seleccionar_semilla_evaluacion)
        self.lbl_perfil = QtWidgets.QLabel()
        perfiles.addWidget(QtWidgets.QLabel('Ambiente'))
        perfiles.addWidget(self.combo_ambiente)
        perfiles.addWidget(QtWidgets.QLabel('Semilla de evaluación'))
        perfiles.addWidget(self.combo_semilla_evaluacion)
        perfiles.addWidget(self.lbl_perfil, 1)
        layout_principal.insertLayout(1, perfiles)
        self._actualizar_estado_bloqueo()

    def configurar_escenario_inicial(self, algoritmo_codigo, ruta_mapa):
        if self._trabajador is not None:
            return
        """Configura los controles iniciales desde la pantalla de bienvenida."""
        self._bloqueo_actualizacion_params = True
        try:
            idx_algo = self.combo_algo.findData(algoritmo_codigo)
            if idx_algo >= 0:
                self.combo_algo.setCurrentIndex(idx_algo)

            idx_mapa = self.combo_mapa.findData(ruta_mapa)
            if idx_mapa >= 0:
                self.combo_mapa.setCurrentIndex(idx_mapa)
            else:
                self.combo_mapa.addItem(Path(ruta_mapa).name + " (Personalizado)", ruta_mapa)
                self.combo_mapa.setCurrentIndex(self.combo_mapa.count() - 1)
        finally:
            self._bloqueo_actualizacion_params = False

        self.badge_algo.setText(self.combo_algo.currentText())
        self.badge_mapa.setText(self.combo_mapa.currentText())
        self.panel_genetico.setVisible(algoritmo_codigo == "genetico")
        self.reiniciar_simulacion()

    def _al_volver_inicio(self):
        if self._trabajador is not None:
            return
        self.detener_animacion()
        self.volver_inicio_signal.emit()

    def _al_cambiar_algoritmo(self):
        if self._trabajador is not None:
            return
        if getattr(self, "_bloqueo_actualizacion_params", False):
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        algo = self.combo_algo.currentData()
        self.badge_algo.setText(self.combo_algo.currentText())
        es_genetico = (algo == "genetico")
        self.panel_genetico.setVisible(es_genetico)
        self.reiniciar_simulacion()

    def _al_cambiar_mapa(self):
        if self._trabajador is not None:
            return
        if getattr(self, "_bloqueo_actualizacion_params", False):
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        self.badge_mapa.setText(self.combo_mapa.currentText())
        self.reiniciar_simulacion()

    def _generar_semilla_aleatoria(self):
        if self._trabajador is not None:
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        nueva = random.randint(0, 999999999)
        self.spin_semilla.setValue(nueva)

    def _examinar_mapa(self):
        if self._trabajador is not None:
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de mapa", str(RAIZ / "maps"), "Archivos de Texto (*.txt);;Todos (*.*)"
        )
        if ruta:
            nombre = Path(ruta).name + " (Personalizado)"
            self.combo_mapa.addItem(nombre, ruta)
            self.combo_mapa.setCurrentIndex(self.combo_mapa.count() - 1)

    def _examinar_politica(self):
        if self._trabajador is not None:
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo JSON de política", str(RAIZ / "results/policies"), "JSON (*.json);;Todos (*.*)"
        )
        if ruta:
            try:
                self.estado_gui.elegir_politica(ruta)
            except (ValueError, OSError, TypeError, KeyError) as error:
                QtWidgets.QMessageBox.warning(self, 'Política inválida', str(error))

    def _cargar_politica_actual(self):
        try:
            self.politica_genetica_obj, info = validar_politica(self.ruta_politica_genetica)
            self.es_politica_entrenada = True
            self.lbl_estado_genetico.setText('Política entrenada: ' + self.ruta_politica_genetica.name)
            p = info['parametros']
            self.lbl_pesos_genetico.setText(f"Congestión={p['peso_congestion']:.2f} | Riesgo={p['peso_riesgo']:.2f} | Bloqueo={p['umbral_bloqueo']}")
        except (ValueError, OSError, TypeError, KeyError):
            self.politica_genetica_obj = None
            self.es_politica_entrenada = False
            self.lbl_estado_genetico.setText('Sin política entrenada válida')
            self.lbl_estado_genetico.setToolTip('Carga un JSON entrenado o abre Entrenar antes de simular con el genético.')
            self.lbl_pesos_genetico.setText('Sin política activa')

    def _politica_compartida(self, ruta):
        if self._trabajador is not None:
            return
        self.ruta_politica_genetica = Path(ruta)
        self._cargar_politica_actual()
        if self.combo_algo.currentData() == 'genetico':
            self.reiniciar_simulacion()

    def _abrir_entrenamiento(self):
        if self._trabajador is not None:
            return
        self.detener_animacion()
        dialogo = TrainingDialog(self)
        dialogo.exec_()

    def _al_entrenar_politica_finalizada(self, nueva_ruta):
        self.ruta_politica_genetica = Path(nueva_ruta).resolve()
        self._cargar_politica_actual()
        self.reiniciar_simulacion()

    def _abrir_benchmark(self):
        if self._trabajador is not None:
            return
        self.detener_animacion()
        pol_ruta = str(self.ruta_politica_genetica) if self.ruta_politica_genetica else None
        dialogo = BenchmarkDialog(self, politica_actual=pol_ruta)
        dialogo.exec_()

    def _construir_motor(self, mostrar_error=True):
        algoritmo = self.combo_algo.currentData()
        mapa_path = self.combo_mapa.currentData()

        if not mapa_path or not Path(mapa_path).is_file():
            if mostrar_error:
                QtWidgets.QMessageBox.critical(self, "Error", f"No se encontró el mapa:\n{mapa_path}")
            return None

        escenario = {
            "mapa": mapa_path,
            "poblacion_inicial": self.spin_poblacion.value(),
            "capacidad_pasillos": self.spin_cap_pasillos.value(),
            "capacidad_salida": self.spin_cap_salida.value(),
            "cantidad_focos": self.spin_focos.value(),
            "distancia_min_salida": self.spin_dist_salida.value(),
            "k": self.spin_k.value(),
            "probabilidad": self.spin_prob_fuego.value(),
            "max_turnos": self.spin_max_turnos.value(),
            "alpha": self.spin_alpha.value(),
            "umbral_bloqueo": self.spin_umbral.value(),
        }

        if algoritmo == "genetico":
            if self.politica_genetica_obj is None:
                self._log_evento('El genético requiere una política entrenada válida.')
                return None
            politica = self.politica_genetica_obj
        else:
            politica = algoritmo

        try:
            motor = MotorSimulacion(politica, escenario, self.spin_semilla.value())
            return motor
        except Exception as error:
            if mostrar_error:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Error de Inicialización",
                    f"No se pudo inicializar la simulación:\n{error}\n"
                    "Verifica que la capacidad del mapa sea suficiente para la población.",
                )
            return None

    def _actualizar_estado_bloqueo(self):
        trabajando = self._trabajador is not None
        """Bloquea controles de parámetros cuando la simulación está en curso (turno > 0 no terminada o animación activa)."""
        en_curso = trabajando
        if self.timer_animacion.isActive():
            en_curso = True
        elif self.motor and self.motor.turno > 0 and not self.motor.terminada:
            en_curso = True

        editable = not en_curso
        for ctrl in self.controles_parametros:
            ctrl.setEnabled(editable)
        self.slider_velocidad.setEnabled(True)
        self.btn_paso.setEnabled(not trabajando and not self.timer_animacion.isActive() and (not self.motor or not self.motor.terminada))
        for w in (self.btn_ejecutar_completa, self.btn_reiniciar, self.btn_restablecer, self.btn_bench, self.btn_volver):
            w.setEnabled(not trabajando)
        if hasattr(self, 'combo_ambiente'):
            self.combo_ambiente.setEnabled(not trabajando)
            self.combo_semilla_evaluacion.setEnabled(editable)
        self.btn_animar.setText('Detener cálculo' if trabajando and not self.timer_animacion.isActive() else 'Pausar' if self.timer_animacion.isActive() else 'Animar')

    def _al_cambiar_velocidad(self, valor):
        """Actualiza el intervalo de animación en tiempo real y la etiqueta descriptiva."""
        t_por_seg = 1000.0 / valor if valor > 0 else 0
        self.lbl_velocidad.setText(f"{valor} ms (~{t_por_seg:.0f} t/s)")
        if self.timer_animacion.isActive():
            self.timer_animacion.setInterval(valor)

    def aplicar_ambiente(self, nombre):
        if self._trabajador is not None or self._aplicando_perfil:
            return
        self.detener_animacion()
        c = cargar_perfil(nombre)
        self._aplicando_perfil = True
        self._bloqueo_actualizacion_params = True
        try:
            self.combo_ambiente.setCurrentIndex(self.combo_ambiente.findData(nombre))
            campos = {'capacidad_pasillos': self.spin_cap_pasillos, 'capacidad_salida': self.spin_cap_salida,
                      'cantidad_focos': self.spin_focos, 'distancia_min_salida': self.spin_dist_salida,
                      'k': self.spin_k, 'probabilidad': self.spin_prob_fuego,
                      'alpha': self.spin_alpha, 'umbral_bloqueo': self.spin_umbral,
                      'max_turnos': self.spin_max_turnos}
            for clave, campo in campos.items():
                campo.setValue(c['parametros'].get(clave, VALORES_INICIALES.get(clave, 0)))
            self.max_turnos = c['parametros']['max_turnos']
            self.spin_poblacion.setValue(c['poblaciones'][0])
            self.spin_poblacion.setToolTip('Poblaciones oficiales: ' + ', '.join(map(str, c['poblaciones'])))
            self.combo_semilla_evaluacion.clear()
            for semilla in c['semillas']:
                self.combo_semilla_evaluacion.addItem(str(semilla), semilla)
            self.spin_semilla.setValue(c['semillas'][0])
            self.lbl_perfil.setText('Oficial · ' + nombre + ' · una simulación exploratoria')
        finally:
            self._aplicando_perfil = False
            self._bloqueo_actualizacion_params = False
        self.estado_gui.elegir_ambiente(nombre)
        self.reiniciar_simulacion()

    def _seleccionar_semilla_evaluacion(self):
        if not self._aplicando_perfil and self._trabajador is None:
            valor = self.combo_semilla_evaluacion.currentData()
            if valor is not None:
                self.spin_semilla.setValue(valor)

    def restablecer_parametros(self):
        self.aplicar_ambiente(self.combo_ambiente.currentData())

    def _al_cambiar_parametro(self):
        if self._trabajador is not None:
            return
        if not self._aplicando_perfil and not getattr(self, '_bloqueo_actualizacion_params', False):
            self.lbl_perfil.setText('Personalizado · parámetros modificados')
        """Maneja cambios interactivos en los controles del panel izquierdo."""
        if getattr(self, "_bloqueo_actualizacion_params", False):
            return
        if self.timer_animacion.isActive() or (self.motor and self.motor.turno > 0 and not self.motor.terminada):
            return
        self.detener_animacion()
        motor_nuevo = self._construir_motor(mostrar_error=False)
        if motor_nuevo is not None:
            self.motor = motor_nuevo
            self._actualizar_interfaz_desde_motor()
            self._log_evento(
                f"Parámetro modificado. Semilla={self.motor.semilla} | Población={len(self.motor.agentes)}"
            )

    def reiniciar_simulacion(self):
        if self._trabajador is not None:
            return
        self.detener_animacion()
        self.motor = self._construir_motor(mostrar_error=True)
        self.txt_eventos.clear()
        self.canvas.setVisible(self.motor is not None)
        if self.motor:
            self._actualizar_interfaz_desde_motor()
            self._log_evento(f"Simulación reiniciada. Semilla={self.motor.semilla} | Población={len(self.motor.agentes)}")
            self.canvas.ajustar_a_vista()
        self._actualizar_estado_bloqueo()

    def avanzar_un_paso(self):
        self._iniciar_trabajo(False)

    def ejecutar_simulacion_completa(self):
        self.detener_animacion()
        self._iniciar_trabajo(True)

    def _iniciar_trabajo(self, completa):
        if self._trabajador is not None:
            return
        if not self.motor:
            self.reiniciar_simulacion()
        if not self.motor or self.motor.terminada:
            return
        try:
            self.estado_gui.adquirir(self)
        except ValueError as error:
            self._log_evento(str(error))
            return
        self._trabajador = TrabajoSimulacion(self.motor, completa, self)
        self._trabajador.finished.connect(self._trabajo_finalizado)
        self._trabajador.start()
        self._actualizar_estado_bloqueo()

    def _trabajo_finalizado(self):
        trabajo = self._trabajador
        self._trabajador = None
        self.estado_gui.liberar(self)
        if trabajo.error:
            self.detener_animacion()
            self._log_evento('Error de simulación: ' + trabajo.error)
        else:
            self.motor = trabajo.motor
            self._actualizar_interfaz_desde_motor()
            if self.motor.terminada:
                self.detener_animacion()
                self._log_evento('Simulación finalizada: ' + str(self.motor.resultado()))
        trabajo.deleteLater()
        self._actualizar_estado_bloqueo()

    def alternar_animacion(self):
        if self._trabajador is not None:
            self.detener_animacion()
            self._trabajador.requestInterruption()
            self._log_evento('Pausa solicitada; terminará al concluir el turno actual.')
            return
        if self.timer_animacion.isActive():
            self.detener_animacion()
        else:
            if not self.motor or self.motor.terminada:
                self.reiniciar_simulacion()
            if self.motor and not self.motor.terminada:
                intervalo = self.slider_velocidad.value()
                self.timer_animacion.start(intervalo)
                self.btn_animar.setText("⏸ Pausar")
                self.btn_animar.setProperty("variant", "warning")
                self.btn_animar.style().unpolish(self.btn_animar)
                self.btn_animar.style().polish(self.btn_animar)
                self._actualizar_estado_bloqueo()

    def detener_animacion(self):
        if self.timer_animacion.isActive():
            self.timer_animacion.stop()
        self.btn_animar.setText("⏯ Animar")
        self.btn_animar.setProperty("variant", "")
        self.btn_animar.style().unpolish(self.btn_animar)
        self.btn_animar.style().polish(self.btn_animar)
        self._actualizar_estado_bloqueo()

    def _paso_animacion(self):
        if not self.motor or self.motor.terminada:
            self.detener_animacion()
            return
        self.avanzar_un_paso()

    def _actualizar_interfaz_desde_motor(self, resultado=None):
        if not self.motor:
            return
        if resultado is None:
            resultado = self.motor.resultado()

        # Actualizar mapa renderizado
        self.canvas.actualizar_mapa(self.motor.mapa, self.motor.agentes, self.motor.focos, self.motor.turno)

        # Actualizar etiquetas y tarjetas
        self.lbl_turno.setText(f"Turno: {self.motor.turno} / {self.motor.escenario['max_turnos']}")

        sup_pct = resultado["supervivencia"] * 100
        self.lbl_supervivencia.setText(f"{sup_pct:.1f}%")
        self.barra_supervivencia.setValue(int(sup_pct))

        # Color según supervivencia
        if sup_pct >= 80:
            self.lbl_supervivencia.setStyleSheet("font-size: 26px; font-weight: 800; color: #10b981;")
        elif sup_pct >= 40:
            self.lbl_supervivencia.setStyleSheet("font-size: 26px; font-weight: 800; color: #f59e0b;")
        else:
            self.lbl_supervivencia.setStyleSheet("font-size: 26px; font-weight: 800; color: #ef4444;")

        total_agentes = len(self.motor.agentes)
        self.val_evacuados.setText(f"{resultado['evacuados']} / {total_agentes}")
        self.val_fallecidos.setText(f"{resultado['fallecidos']} / {total_agentes}")
        self.val_pendientes.setText(f"{resultado['pendientes']} / {total_agentes}")

        ult = resultado["turno_ultimo_evacuado"]
        self.val_ultimo.setText(str(ult) if ult is not None else "N/D")

        motivo = resultado["motivo_termino"]
        if motivo is None:
            self.val_motivo.setText("En curso")
            self.val_motivo.setStyleSheet("color: #38bdf8;")
        elif motivo == "sin_agentes_pendientes":
            self.val_motivo.setText("Evacuación terminada")
            self.val_motivo.setStyleSheet("color: #10b981;")
        elif motivo == "max_turnos":
            self.val_motivo.setText("Límite de turnos alcanzado")
            self.val_motivo.setStyleSheet("color: #f59e0b;")
        else:
            self.val_motivo.setText(str(motivo))

        self.val_movimientos.setText(str(resultado["movimientos"]))
        self.val_esperas.setText(str(resultado["esperas"]))
        self.val_planificaciones.setText(str(resultado["planificaciones"]))
        self._actualizar_estado_bloqueo()

    def _log_evento(self, texto):
        self.txt_eventos.appendPlainText(f"[T={self.motor.turno if self.motor else 0}] {texto}")
        self.txt_eventos.verticalScrollBar().setValue(self.txt_eventos.verticalScrollBar().maximum())
