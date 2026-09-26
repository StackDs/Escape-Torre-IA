import numpy as np

from .celda import Celda


def cargar_mapa(path):
    """Carga celdas nuevas y valida la estructura del archivo de texto."""
    with open(path, "r", encoding="utf-8") as archivo:
        lineas = archivo.read().splitlines()

    if len(lineas) == 0 or len(lineas[0]) == 0:
        raise ValueError("El mapa no puede estar vacio.")

    filas = len(lineas)
    columnas = len(lineas[0])
    salidas = 0
    for linea in lineas:
        if len(linea) != columnas:
            raise ValueError("Todas las filas del mapa deben tener igual longitud.")
        for simbolo in linea:
            if simbolo not in ("#", ".", "E"):
                raise ValueError("El mapa contiene un simbolo desconocido: " + simbolo)
            if simbolo == "E":
                salidas += 1
    if salidas != 1:
        raise ValueError("El mapa debe tener exactamente una salida.")

    mapa = np.empty((filas, columnas), dtype=object)
    for fila in range(filas):
        for columna in range(columnas):
            simbolo = lineas[fila][columna]
            if simbolo == "#":
                capacidad = 0
            elif simbolo == ".":
                capacidad = 4
            else:
                capacidad = 2
            mapa[fila, columna] = Celda(simbolo, capacidad)

    return mapa
