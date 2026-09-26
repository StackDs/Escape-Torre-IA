from enum import Enum

class State(Enum):
    ACTIVO = 1
    ESPERANDO = 2
    EVACUADO = 3
    MUERTO = 4


class Agente:

    def __init__(self, id_agente, fila, columna):
        self.id_agente = id_agente

        # Posicion en la matriz
        self.fila = fila
        self.columna = columna

        # Activo inicialmente
        self.estado = State.ACTIVO

        # Proximas posiciones a visitar

        self.ruta = []

        # Se completan en caso de ocurrir la accion
        self.turno_evacuacion = None
        self.turno_fallecimiento = None

        # Contadores para analisis estadisticos

        self.movimientos = 0
        self.esperas = 0
        self.turnos_bloqueado = 0
        self.replanificaciones = 0

    def set_estado(self,estado : State):
            self.estado = estado

    def obtener_posicion(self):
            return (self.fila, self.columna)

    def asignar_ruta(self, ruta):
            self.ruta = ruta
            self.replanificaciones += 1

    def siguiente_posicion(self):
            if len(self.ruta) == 0:
                return None
            return self.ruta[0]

    def borrar_ruta(self):
            self.ruta.clear()
        
