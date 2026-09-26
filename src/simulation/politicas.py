
import math

from ..models.agente import State
from ..algorithms.Uninformed.BFS import bfs
from ..algorithms.Uninformed.DFS import dfs
from ..algorithms.Uninformed.UCS import ucs
from ..algorithms.Informed.A_Star import a_star
from ..algorithms.Informed.IDA_Star import ida_star
from ..algorithms.Informed.Greedy import greedy


BUSQUEDAS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "a_star": a_star,
    "ida_star": ida_star,
    "greedy": greedy
}

# Comprueba pasos ortogonales transitables y llegada a la salida
def ruta_valida(mapa, inicio, ruta):
    filas, columnas = mapa.shape
    anterior = inicio
    for paso in ruta:
        if not isinstance(paso, (tuple, list)) or len(paso) != 2:
            return False
        fila, columna = paso
        if type(fila) is not int or type(columna) is not int:
            return False
        if not (0 <= fila < filas and 0 <= columna < columnas):
            return False
        if abs(fila - anterior[0]) + abs(columna - anterior[1]) != 1:
            return False
        celda = mapa[fila, columna]
        if celda.simbolo == "#" or celda.quemada or celda.capacidad <= 0:
            return False
        # No permitir continuar caminando despues de haber evacuado.
        if mapa[anterior].simbolo == "E":
            return False
        anterior = (fila, columna)
    return mapa[anterior].simbolo == "E" and not mapa[anterior].quemada


class PoliticaBusqueda:
    def __init__(self, algoritmo="bfs", alpha=1.0, umbral_bloqueo=3):
        if algoritmo not in BUSQUEDAS:
            raise ValueError("Algoritmo desconocido: " + str(algoritmo))
        if not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or alpha < 0:
            raise ValueError("Alpha debe ser finito y no negativo.")
        if type(umbral_bloqueo) is not int or umbral_bloqueo < 1:
            raise ValueError("El umbral de bloqueo debe ser un entero positivo.")
        self.algoritmo = algoritmo
        self.alpha = alpha
        self.umbral_bloqueo = umbral_bloqueo

    def planificar(self, mapa, inicio):
        busqueda = BUSQUEDAS[self.algoritmo]
        if self.algoritmo in ("ucs", "a_star", "ida_star"):
            return busqueda(mapa, inicio, self.alpha)
        return busqueda(mapa, inicio)

    def necesita_replanificar(self, mapa, agente, ruta_comprobada=False):
        if agente.estado not in (State.ACTIVO, State.ESPERANDO):
            return False
        if mapa[agente.obtener_posicion()].simbolo == "E":
            return False
        if len(agente.ruta) == 0:
            return True
        # El motor puede haber validado ya la ruta en esta misma fase.
        if not ruta_comprobada and not ruta_valida(mapa, agente.obtener_posicion(), agente.ruta):
            return True
        return agente.turnos_bloqueado >= self.umbral_bloqueo
