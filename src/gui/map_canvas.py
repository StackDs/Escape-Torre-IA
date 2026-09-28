"""Componente QGraphicsView de alto rendimiento para renderización y visualización del mapa."""

from PyQt5 import QtCore, QtGui, QtWidgets
from src.models.agente import State


class MapCanvas(QtWidgets.QGraphicsView):
    """Vista gráfica interactiva optimizada de la grilla del edificio, fuego y agentes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self.scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setRenderHint(QtGui.QPainter.TextAntialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#090d16")))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.tile_size = 22
        self.filas = 0
        self.columnas = 0
        self._mapa = None
        self._agentes = []
        self._factor_zoom_acumulado = 1.0

        # Estructuras persistentes para renderizado a 60+ FPS
        self._items_celdas = {}
        self._items_dinamicos = []
        self._celdas_quemadas_previas = set()

        # Pinceles y lápices cacheados para alto rendimiento
        self.brush_muro = QtGui.QBrush(QtGui.QColor("#181f2f"))
        self.pen_muro = QtGui.QPen(QtGui.QColor("#2c384e"), 1)

        self.brush_pasillo = QtGui.QBrush(QtGui.QColor("#334155"))
        self.pen_pasillo = QtGui.QPen(QtGui.QColor("#475569"), 1)

        self.brush_salida = QtGui.QBrush(QtGui.QColor("#10b981"))
        self.pen_salida = QtGui.QPen(QtGui.QColor("#059669"), 2)

        self.brush_fuego = QtGui.QBrush(QtGui.QColor("#ef4444"))
        self.pen_fuego = QtGui.QPen(QtGui.QColor("#dc2626"), 1)

        self.brush_agente = QtGui.QBrush(QtGui.QColor("#38bdf8"))
        self.pen_agente = QtGui.QPen(QtGui.QColor("#0284c7"), 1)

        self.brush_fallecido = QtGui.QBrush(QtGui.QColor("#7f1d1d"))
        self.pen_fallecido = QtGui.QPen(QtGui.QColor("#991b1b"), 1)

        self.font_salida = QtGui.QFont("Segoe UI", int(self.tile_size * 0.55), QtGui.QFont.Bold)
        self.font_badge = QtGui.QFont("Segoe UI", int(self.tile_size * 0.45), QtGui.QFont.Bold)

    def _construir_escena(self, mapa):
        """Construye los rectángulos base estáticos del mapa una sola vez."""
        self.scene.clear()
        self._items_celdas.clear()
        self._items_dinamicos.clear()
        self._celdas_quemadas_previas.clear()

        filas, columnas = mapa.shape
        self.filas = filas
        self.columnas = columnas
        ts = self.tile_size

        for r in range(filas):
            for c in range(columnas):
                celda = mapa[r, c]
                x = c * ts
                y = r * ts
                simbolo = celda.simbolo

                if simbolo == "#":
                    item = self.scene.addRect(x, y, ts, ts, self.pen_muro, self.brush_muro)
                    item.setToolTip(f"Muro ({r}, {c})")
                elif simbolo == "E":
                    item = self.scene.addRect(x, y, ts, ts, self.pen_salida, self.brush_salida)
                    texto = self.scene.addSimpleText("E", self.font_salida)
                    texto.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
                    texto.setPos(
                        x + (ts - texto.boundingRect().width()) / 2,
                        y + (ts - texto.boundingRect().height()) / 2,
                    )
                    item.setToolTip(f"Salida ({r}, {c}) | Capacidad: {celda.capacidad}")
                else:
                    item = self.scene.addRect(x, y, ts, ts, self.pen_pasillo, self.brush_pasillo)
                    item.setToolTip(f"Pasillo ({r}, {c}) | Capacidad: {celda.capacidad}")

                self._items_celdas[(r, c)] = item

        self.scene.setSceneRect(0, 0, columnas * ts, filas * ts)

    def actualizar_mapa(self, mapa, agentes=None, focos=None, turno=0):
        """Actualiza incrementalmente el estado de celdas quemadas y posiciones de agentes."""
        if mapa is None:
            return

        filas, columnas = mapa.shape
        if (
            (filas, columnas) != (self.filas, self.columnas)
            or len(self._items_celdas) != filas * columnas
            or self._mapa is not mapa
        ):
            self._construir_escena(mapa)

        self._mapa = mapa
        self._agentes = agentes or []
        ts = self.tile_size

        # Estado de celdas quemadas
        celdas_quemadas_actuales = set()
        for r in range(filas):
            for c in range(columnas):
                if mapa[r, c].quemada:
                    celdas_quemadas_actuales.add((r, c))

        if turno == 0 or not celdas_quemadas_actuales:
            for (r, c) in self._celdas_quemadas_previas:
                if (r, c) in self._items_celdas:
                    simbolo = mapa[r, c].simbolo
                    if simbolo == "E":
                        self._items_celdas[(r, c)].setBrush(self.brush_salida)
                        self._items_celdas[(r, c)].setPen(self.pen_salida)
                    else:
                        self._items_celdas[(r, c)].setBrush(self.brush_pasillo)
                        self._items_celdas[(r, c)].setPen(self.pen_pasillo)
            self._celdas_quemadas_previas.clear()
        else:
            # Restaurar celdas recuperadas si hubo reinicio
            recuperadas = self._celdas_quemadas_previas - celdas_quemadas_actuales
            for (r, c) in recuperadas:
                if (r, c) in self._items_celdas:
                    simbolo = mapa[r, c].simbolo
                    brush = self.brush_salida if simbolo == "E" else self.brush_pasillo
                    pen = self.pen_salida if simbolo == "E" else self.pen_pasillo
                    self._items_celdas[(r, c)].setBrush(brush)
                    self._items_celdas[(r, c)].setPen(pen)

            # Pintar las nuevas celdas quemadas en rojo
            nuevas_quemadas = celdas_quemadas_actuales - self._celdas_quemadas_previas
            for (r, c) in nuevas_quemadas:
                if (r, c) in self._items_celdas:
                    self._items_celdas[(r, c)].setBrush(self.brush_fuego)
                    self._items_celdas[(r, c)].setPen(self.pen_fuego)

            self._celdas_quemadas_previas = celdas_quemadas_actuales

        # Eliminar items dinámicos del turno anterior (agentes y marcadores)
        for item in self._items_dinamicos:
            self.scene.removeItem(item)
        self._items_dinamicos.clear()

        # Separar agentes vivos y muertos por celda
        ocupacion_activos = {}
        ocupacion_fallecidos = {}
        for agente in self._agentes:
            pos = agente.obtener_posicion()
            if agente.estado in (State.ACTIVO, State.ESPERANDO):
                ocupacion_activos.setdefault(pos, []).append(agente)
            elif agente.estado == State.MUERTO:
                ocupacion_fallecidos.setdefault(pos, []).append(agente)

        # Marcador visual de fuego sobre celdas quemadas
        for (r, c) in celdas_quemadas_actuales:
            x = c * ts
            y = r * ts
            fuego_txt = self.scene.addSimpleText("🔥", self.font_badge)
            fuego_txt.setBrush(QtGui.QBrush(QtGui.QColor("#fef08a")))
            fuego_txt.setPos(
                x + (ts - fuego_txt.boundingRect().width()) / 2,
                y + (ts - fuego_txt.boundingRect().height()) / 2,
            )
            self._items_dinamicos.append(fuego_txt)

        # Dibujar agentes fallecidos con marca en cruz
        for (r, c), muertos in ocupacion_fallecidos.items():
            x = c * ts
            y = r * ts
            cruz = self.scene.addSimpleText("✖", self.font_badge)
            cruz.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
            cruz.setPos(
                x + (ts - cruz.boundingRect().width()) / 2,
                y + (ts - cruz.boundingRect().height()) / 2,
            )
            cruz.setToolTip(f"Agente(s) fallecido(s): {len(muertos)}")
            self._items_dinamicos.append(cruz)

        # Dibujar agentes activos
        for (r, c), agentes_aqui in ocupacion_activos.items():
            n = len(agentes_aqui)
            x = c * ts
            y = r * ts
            radio = ts * 0.38
            offset = (ts - (radio * 2)) / 2
            circulo = self.scene.addEllipse(
                x + offset, y + offset, radio * 2, radio * 2,
                self.pen_agente, self.brush_agente
            )
            ids_str = ", ".join(str(a.id_agente) for a in agentes_aqui)
            circulo.setToolTip(f"Agentes activos: {n} (IDs: {ids_str})")
            self._items_dinamicos.append(circulo)

            if n > 1:
                badge = self.scene.addSimpleText(str(n), self.font_badge)
                badge.setBrush(QtGui.QBrush(QtGui.QColor("#0f172a")))
                badge.setPos(
                    x + (ts - badge.boundingRect().width()) / 2,
                    y + (ts - badge.boundingRect().height()) / 2,
                )
                self._items_dinamicos.append(badge)

    def ajustar_a_vista(self):
        """Ajusta el zoom para que todo el mapa quepa perfectamente en la ventana."""
        if self.filas > 0 and self.columnas > 0:
            self.fitInView(self.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
            self._factor_zoom_acumulado = 1.0

    def wheelEvent(self, event):
        """Permite hacer zoom con la rueda del ratón dentro de cotas seguras."""
        factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
        nuevo_factor = self._factor_zoom_acumulado * factor
        if 0.3 <= nuevo_factor <= 15.0:
            self._factor_zoom_acumulado = nuevo_factor
            self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
