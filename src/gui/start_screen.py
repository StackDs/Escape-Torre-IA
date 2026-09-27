"""Pantalla de inicio para la selección inicial de algoritmo y mapa."""

from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from .experimentos import estado_compartido, AMBIENTES

RAIZ = Path(__file__).resolve().parents[2]

ALGORITMOS = [
    ("bfs", "BFS (Búsqueda en Anchura)", "Búsqueda ciega, óptima en número de pasos para costos uniformes."),
    ("dfs", "DFS (Búsqueda en Profundidad)", "Búsqueda ciega explorando ramas profundas; no garantiza ruta óptima."),
    ("ucs", "UCS (Costo Uniforme / Dijkstra)", "Encuentra la ruta de costo mínimo considerando congestión de celdas."),
    ("a_star", "A* (A-Estrella)", "Búsqueda informada con heurística Manhattan admisible y consistente."),
    ("greedy", "Greedy (Búsqueda Voraz)", "Guiada exclusivamente por la distancia heurística a la salida."),
    ("ida_star", "IDA* (A* con Profundización Iterativa)", "Umbrales sucesivos de f(n), con tabla de costos y grafo preparado."),
    ("genetico", "Algoritmo Genético", "Política con pesos adaptativos (congestión, riesgo al fuego, umbral de bloqueo)."),
]

MAPAS_DISPONIBLES = [
    ("maps/bottleneck.txt", "Cuello de Botella (50x50)", "Pasillo estrecho central hacia la salida, alta probabilidad de congestión."),
    ("maps/corporate_maze.txt", "Laberinto Corporativo (50x50)", "Múltiples pasillos interconectados y rutas alternativas."),
    ("maps/open_area.txt", "Área Abierta (50x50)", "Espacio amplio con baja obstrucción, ideal para evaluar velocidad de dispersión."),
]


class StartScreen(QtWidgets.QWidget):
    """Pantalla de bienvenida e inicio del simulador."""

    # Señal emitida al hacer clic en entrar: (algoritmo_id, ruta_mapa)
    iniciar_simulacion_signal = QtCore.pyqtSignal(str, str)
    abrir_benchmark_signal = QtCore.pyqtSignal()
    abrir_entrenamiento_signal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estado_gui = estado_compartido(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.setAlignment(QtCore.Qt.AlignCenter)

        # Contenedor central tipo tarjeta
        tarjeta = QtWidgets.QFrame()
        tarjeta.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 25px;
                max-width: 680px;
            }
        """)
        tarjeta_layout = QtWidgets.QVBoxLayout(tarjeta)
        tarjeta_layout.setSpacing(18)

        # Encabezado
        titulo = QtWidgets.QLabel("ESCAPE DE LA TORRE IA")
        titulo.setStyleSheet("font-size: 26px; font-weight: 800; color: #60a5fa;")
        titulo.setAlignment(QtCore.Qt.AlignCenter)
        tarjeta_layout.addWidget(titulo)

        subtitulo = QtWidgets.QLabel("Simulador de Evacuación de Emergencia con Algoritmos de Búsqueda y Optimización")
        subtitulo.setStyleSheet("font-size: 13px; color: #94a3b8;")
        subtitulo.setAlignment(QtCore.Qt.AlignCenter)
        subtitulo.setWordWrap(True)
        tarjeta_layout.addWidget(subtitulo)

        # Separador horizontal
        linea = QtWidgets.QFrame()
        linea.setFrameShape(QtWidgets.QFrame.HLine)
        linea.setStyleSheet("background-color: #334155; height: 1px;")
        tarjeta_layout.addWidget(linea)

        self.combo_ambiente = QtWidgets.QComboBox()
        for nombre in AMBIENTES:
            self.combo_ambiente.addItem(nombre.capitalize(), nombre)
        self.combo_ambiente.setCurrentIndex(0)
        self.combo_ambiente.currentIndexChanged.connect(lambda: self.estado_gui.elegir_ambiente(self.combo_ambiente.currentData()))
        self.estado_gui.ambiente_cambiado.connect(lambda nombre: self.combo_ambiente.setCurrentIndex(self.combo_ambiente.findData(nombre)))
        tarjeta_layout.addWidget(QtWidgets.QLabel('Ambiente experimental'))
        tarjeta_layout.addWidget(self.combo_ambiente)

        # Selección de Algoritmo
        grupo_algo = QtWidgets.QGroupBox("1. Selecciona el Algoritmo")
        layout_algo = QtWidgets.QVBoxLayout(grupo_algo)
        self.combo_algoritmo = QtWidgets.QComboBox()
        for codigo, nombre, _ in ALGORITMOS:
            self.combo_algoritmo.addItem(nombre, codigo)
        self.combo_algoritmo.setCurrentIndex(3)  # A* por defecto
        layout_algo.addWidget(self.combo_algoritmo)

        self.lbl_desc_algo = QtWidgets.QLabel(ALGORITMOS[3][2])
        self.lbl_desc_algo.setStyleSheet("color: #94a3b8; font-style: italic;")
        self.lbl_desc_algo.setWordWrap(True)
        layout_algo.addWidget(self.lbl_desc_algo)
        self.combo_algoritmo.currentIndexChanged.connect(self._al_cambiar_algoritmo)
        tarjeta_layout.addWidget(grupo_algo)

        # Selección de Mapa
        grupo_mapa = QtWidgets.QGroupBox("2. Selecciona el Mapa")
        layout_mapa = QtWidgets.QVBoxLayout(grupo_mapa)
        
        mapa_row = QtWidgets.QHBoxLayout()
        self.combo_mapa = QtWidgets.QComboBox()
        for ruta_rel, nombre, _ in MAPAS_DISPONIBLES:
            ruta_abs = str((RAIZ / ruta_rel).resolve())
            self.combo_mapa.addItem(nombre, ruta_abs)
        mapa_row.addWidget(self.combo_mapa, 1)

        btn_examinar = QtWidgets.QPushButton("Examinar...")
        btn_examinar.setProperty("variant", "secondary")
        btn_examinar.clicked.connect(self._examinar_mapa)
        mapa_row.addWidget(btn_examinar)
        layout_mapa.addLayout(mapa_row)

        self.lbl_desc_mapa = QtWidgets.QLabel(MAPAS_DISPONIBLES[0][2])
        self.lbl_desc_mapa.setStyleSheet("color: #94a3b8; font-style: italic;")
        self.lbl_desc_mapa.setWordWrap(True)
        layout_mapa.addWidget(self.lbl_desc_mapa)
        self.combo_mapa.currentIndexChanged.connect(self._al_cambiar_mapa)
        tarjeta_layout.addWidget(grupo_mapa)

        # Botón Principal
        btn_iniciar = QtWidgets.QPushButton("▶ Entrar a la Simulación")
        btn_iniciar.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                padding: 12px;
                background-color: #3b82f6;
                color: white;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        btn_iniciar.clicked.connect(self._iniciar_simulacion)
        tarjeta_layout.addWidget(btn_iniciar)

        # Botones de accesos directos secundarios
        fila_secundaria = QtWidgets.QHBoxLayout()
        btn_bench = QtWidgets.QPushButton("📊 Ejecutar Benchmark")
        btn_bench.setProperty("variant", "secondary")
        btn_bench.clicked.connect(self.abrir_benchmark_signal.emit)
        fila_secundaria.addWidget(btn_bench)

        btn_entrenar = QtWidgets.QPushButton("🧬 Entrenar Genético")
        btn_entrenar.setProperty("variant", "secondary")
        btn_entrenar.clicked.connect(self.abrir_entrenamiento_signal.emit)
        fila_secundaria.addWidget(btn_entrenar)

        tarjeta_layout.addLayout(fila_secundaria)

        layout.addWidget(tarjeta)

    def _al_cambiar_algoritmo(self, index):
        if 0 <= index < len(ALGORITMOS):
            self.lbl_desc_algo.setText(ALGORITMOS[index][2])

    def _al_cambiar_mapa(self, index):
        if 0 <= index < len(MAPAS_DISPONIBLES):
            self.lbl_desc_mapa.setText(MAPAS_DISPONIBLES[index][2])
        else:
            self.lbl_desc_mapa.setText("Mapa personalizado cargado.")

    def _examinar_mapa(self):
        ruta, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de mapa", str(RAIZ / "maps"), "Archivos de Texto (*.txt);;Todos (*.*)"
        )
        if ruta:
            nombre = Path(ruta).name + " (Personalizado)"
            self.combo_mapa.addItem(nombre, ruta)
            self.combo_mapa.setCurrentIndex(self.combo_mapa.count() - 1)

    def set_algoritmo(self, codigo):
        """Selecciona el algoritmo inicial si coincide con las opciones disponibles."""
        if not codigo:
            return
        idx = self.combo_algoritmo.findData(codigo.lower().strip())
        if idx >= 0:
            self.combo_algoritmo.setCurrentIndex(idx)

    def set_mapa(self, ruta):
        """Selecciona o añade el mapa inicial si la ruta es válida."""
        if not ruta:
            return
        ruta_abs = str(Path(ruta).resolve())
        idx = self.combo_mapa.findData(ruta_abs)
        if idx >= 0:
            self.combo_mapa.setCurrentIndex(idx)
        elif Path(ruta_abs).is_file():
            self.combo_mapa.addItem(Path(ruta_abs).name + " (Personalizado)", ruta_abs)
            self.combo_mapa.setCurrentIndex(self.combo_mapa.count() - 1)

    def _iniciar_simulacion(self):
        algo_codigo = self.combo_algoritmo.currentData()
        mapa_ruta = self.combo_mapa.currentData()
        self.iniciar_simulacion_signal.emit(algo_codigo, mapa_ruta)
