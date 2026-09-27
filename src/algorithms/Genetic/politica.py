import heapq
import json
from collections import deque
from pathlib import Path

from .individuo import Individuo
from ...models.agente import State


def manhattan(posicion, destino):
    return abs(posicion[0] - destino[0]) + abs(posicion[1] - destino[1])


def calcular_riesgos(filas, columnas, fuego):
    """Calcula distancia Manhattan al fuego para toda la grilla en una pasada.

    Se parte de todos los focos a la vez. Se atraviesan tambien los muros
    porque el riesgo original mide distancia geometrica, no caminos libres.
    Esto no propaga el incendio ni modifica el mapa.
    """
    if not fuego:
        return {}
    distancias = {posicion: 0 for posicion in fuego}
    pendientes = deque(fuego)
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while pendientes:
        actual = pendientes.popleft()
        for cambio_fila, cambio_columna in direcciones:
            vecino = (actual[0] + cambio_fila, actual[1] + cambio_columna)
            if not (0 <= vecino[0] < filas and 0 <= vecino[1] < columnas):
                continue
            if vecino in distancias:
                continue
            distancias[vecino] = distancias[actual] + 1
            pendientes.append(vecino)
    return {posicion: 1 / (1 + distancia) for posicion, distancia in distancias.items()}


class PoliticaGenetica:
    """A* con pesos aprendidos y una regla de replanificacion.

    Consulta el mapa sin modificarlo. El motor aplica movimientos,
    espera, fuego y transiciones de estado.
    """

    def __init__(self, individuo):
        self.individuo = individuo.copiar()
        self._estado_riesgo = None
        self._riesgos = {}

    def necesita_replanificar(self, mapa, agente):
        if agente.estado not in (State.ACTIVO, State.ESPERANDO):
            return False

        posicion = agente.obtener_posicion()
        if mapa[posicion].simbolo == "E":
            return False
        if len(agente.ruta) == 0:
            return True

        filas, columnas = mapa.shape
        anterior = posicion
        for paso in agente.ruta:
            fila, columna = paso
            if not (0 <= fila < filas and 0 <= columna < columnas):
                return True
            celda = mapa[paso]
            if celda.simbolo == "#" or celda.quemada or celda.capacidad <= 0:
                return True
            if manhattan(anterior, paso) != 1:
                return True
            anterior = paso

        # Una ruta debe terminar en la salida.
        if mapa[agente.ruta[-1]].simbolo != "E":
            return True

        # La saturacion temporal no invalida inmediatamente la ruta.
        return agente.turnos_bloqueado >= self.individuo.umbral_bloqueo

    def planificar(self, mapa, inicio):
        """Devuelve ruta sin inicio, [] al llegar, o None si no hay ruta.

        El mapa debe permanecer estable durante esta llamada.
        El riesgo mide proximidad Manhattan, no probabilidad de incendio.
        """
        filas, columnas = mapa.shape
        fila_inicial, columna_inicial = inicio
        if not (0 <= fila_inicial < filas and 0 <= columna_inicial < columnas):
            return None

        inicial = mapa[inicio]
        if inicial.simbolo == "#" or inicial.quemada or inicial.capacidad <= 0:
            return None

        salida = None
        fuego = []
        for fila in range(filas):
            for columna in range(columnas):
                celda = mapa[fila, columna]
                if celda.quemada:
                    fuego.append((fila, columna))
                if celda.simbolo == "E":
                    if salida is not None:
                        return None
                    salida = (fila, columna)

        if salida is None or mapa[salida].quemada or mapa[salida].capacidad <= 0:
            return None
        if inicio == salida:
            return []

        # Los agentes comparten esta politica dentro de la misma simulacion.
        # Recalcular solo si cambia el fuego o el tamaño de la grilla.
        riesgos = {}
        if self.individuo.peso_riesgo > 0:
            estado_riesgo = (filas, columnas, tuple(fuego))
            if estado_riesgo != self._estado_riesgo:
                self._riesgos = calcular_riesgos(filas, columnas, fuego)
                self._estado_riesgo = estado_riesgo
            riesgos = self._riesgos

        pendientes = [(manhattan(inicio, salida), 0, 0.0, inicio)]
        costos = {inicio: 0.0}
        anteriores = {}
        orden = 0
        direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        while len(pendientes) > 0:
            _, _, costo_actual, actual = heapq.heappop(pendientes)
            if costo_actual > costos[actual]:
                continue
            if actual == salida:
                ruta = []
                posicion = actual
                while posicion != inicio:
                    ruta.append(posicion)
                    posicion = anteriores[posicion]
                ruta.reverse()
                return ruta

            for cambio_fila, cambio_columna in direcciones:
                fila = actual[0] + cambio_fila
                columna = actual[1] + cambio_columna
                if not (0 <= fila < filas and 0 <= columna < columnas):
                    continue

                vecino = (fila, columna)
                celda = mapa[vecino]
                if celda.simbolo == "#" or celda.quemada or celda.capacidad <= 0:
                    continue

                congestion = (len(celda.agentes) / celda.capacidad) ** 2
                costo_paso = (
                    1
                    + self.individuo.peso_congestion * congestion
                    + self.individuo.peso_riesgo * riesgos.get(vecino, 0.0)
                )
                nuevo_costo = costo_actual + costo_paso
                if vecino not in costos or nuevo_costo < costos[vecino]:
                    costos[vecino] = nuevo_costo
                    anteriores[vecino] = actual
                    orden += 1
                    prioridad = nuevo_costo + manhattan(vecino, salida)
                    heapq.heappush(pendientes, (prioridad, orden, nuevo_costo, vecino))

        return None


def obtener_politica_genetica(ruta=None, permitir_por_defecto=True):
    """Carga una politica genetica desde archivo o devuelve una con pesos por defecto.

    Retorna: (politica, es_entrenada, info_dict)
    """
    if ruta is None:
        ruta = Path(__file__).resolve().parents[3] / "results/policies/mejor.json"
    else:
        ruta = Path(ruta).resolve()

    if ruta.is_file():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            individuo = Individuo(**datos["parametros"])
            if "aptitud_entrenamiento" in datos:
                individuo.aptitud = datos["aptitud_entrenamiento"]
            return PoliticaGenetica(individuo), True, datos
        except Exception:
            if not permitir_por_defecto:
                raise

    if permitir_por_defecto:
        individuo = Individuo(peso_congestion=1.0, peso_riesgo=2.0, umbral_bloqueo=3)
        info = {
            "parametros": individuo.parametros(),
            "estado": "no_entrenado_por_defecto",
            "archivo": str(ruta)
        }
        return PoliticaGenetica(individuo), False, info

    raise FileNotFoundError("No existe el archivo de politica entrenada: " + str(ruta))
