import heapq

from ...models.agente import State


def manhattan(posicion, destino):
    return abs(posicion[0] - destino[0]) + abs(posicion[1] - destino[1])


class PoliticaGenetica:
    """A* con pesos aprendidos y una regla de replanificacion.

    Consulta el mapa sin modificarlo. El motor aplica movimientos,
    espera, fuego y transiciones de estado.
    """

    def __init__(self, individuo):
        self.individuo = individuo.copiar()

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

        pendientes = [(manhattan(inicio, salida), 0, 0.0, inicio)]
        costos = {inicio: 0.0}
        anteriores = {}
        riesgos = {}
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

                # Calcular una vez por celda durante esta busqueda.
                if vecino not in riesgos:
                    riesgo = 0.0
                    if len(fuego) > 0 and self.individuo.peso_riesgo > 0:
                        distancia = min(manhattan(vecino, foco) for foco in fuego)
                        riesgo = 1 / (1 + distancia)
                    riesgos[vecino] = riesgo

                congestion = (len(celda.agentes) / celda.capacidad) ** 2
                costo_paso = (
                    1
                    + self.individuo.peso_congestion * congestion
                    + self.individuo.peso_riesgo * riesgos[vecino]
                )
                nuevo_costo = costo_actual + costo_paso
                if vecino not in costos or nuevo_costo < costos[vecino]:
                    costos[vecino] = nuevo_costo
                    anteriores[vecino] = actual
                    orden += 1
                    prioridad = nuevo_costo + manhattan(vecino, salida)
                    heapq.heappush(pendientes, (prioridad, orden, nuevo_costo, vecino))

        return None
