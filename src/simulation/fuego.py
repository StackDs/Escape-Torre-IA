
import math
import random


def seleccionar_focos(mapa, cantidad, semilla=0, distancia_min_salida=0):
    # Elige posiciones iniciales distintas sin modificar el mapa

    if type(cantidad) is not int or cantidad < 0:
        return None
    if type(distancia_min_salida) is not int or distancia_min_salida < 0:
        return None

    filas, columnas = mapa.shape
    salidas = []
    if distancia_min_salida > 0:
        for fila in range(filas):
            for columna in range(columnas):
                if mapa[fila, columna].simbolo == "E":
                    salidas.append((fila, columna))

    candidatas = []

    # Recorrido fijo para que la misma semilla produzca los mismos focos
    for fila in range(filas):
        for columna in range(columnas):
            celda = mapa[fila, columna]
            if celda.simbolo != "." or celda.quemada:
                continue
            if len(celda.agentes) > 0:
                continue
            if distancia_min_salida > 0 and salidas:
                dist_min = min(abs(fila - sf) + abs(columna - sc) for sf, sc in salidas)
                if dist_min < distancia_min_salida:
                    continue
            candidatas.append((fila, columna))

    if cantidad > len(candidatas):
        return None

    azar_inicial = random.Random(semilla)
    return sorted(azar_inicial.sample(candidatas, cantidad))



# Crea focos de incendio de forma aleatoria y reporta las posiciones encendidas
def encender_focos(mapa, focos):

    filas, columnas = mapa.shape
    posiciones = []
    vistos = set()

    for foco in focos:
        fila, columna = foco
        if not (0 <= fila < filas and 0 <= columna < columnas):
            return None

        posicion = (fila, columna)
        if posicion in vistos:
            return None

        celda = mapa[posicion]
        if celda.simbolo != "." or celda.quemada:
            return None
        if len(celda.agentes) > 0:
            return None

        vistos.add(posicion)
        posiciones.append(posicion)

    posiciones.sort()
    for posicion in posiciones:
        mapa[posicion].quemar()

    return posiciones

# Propaga cada k turnos el fuego y devuelve las posiciones recien quemadas
def propagar_fuego(mapa, turno, k, probabilidad, azar):

    if type(turno) is not int or turno < 0:
        return None
    if type(k) is not int or k <= 0:
        return None
    if not math.isfinite(probabilidad) or not 0 <= probabilidad <= 1:
        return None

    # En el turno cero solo se colocan los focos iniciales
    if turno == 0 or turno % k != 0:
        return []

    filas, columnas = mapa.shape
    candidatas = set()
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    # Identificamos a los vecinos del fuego existente
    for fila in range(filas):
        for columna in range(columnas):
            if not mapa[fila, columna].quemada:
                continue
            if mapa[fila, columna].simbolo == "#":
                continue

            for cambio_fila, cambio_columna in direcciones:
                nueva_fila = fila + cambio_fila
                nueva_columna = columna + cambio_columna
                if not (0 <= nueva_fila < filas and 0 <= nueva_columna < columnas):
                    continue

                vecino = (nueva_fila, nueva_columna)
                celda = mapa[vecino]
                if celda.simbolo in (".", "E") and not celda.quemada:
                    candidatas.add(vecino)

    # El conjunto elimina duplicados y sorted fija el orden de los sorteos
    nuevas = []
    for posicion in sorted(candidatas):
        if azar.random() < probabilidad:
            nuevas.append(posicion)

    # Aplicar todos los incendios decididos
    for posicion in nuevas:
        mapa[posicion].quemar()

    return nuevas
