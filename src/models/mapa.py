from celda import Celda
import numpy as np


def cargar_mapa(path):
    # Cargamos el mapa a un arreglo auxiliar

    mapaTxt = open(path,"r", encoding="utf-8")
    lineas = mapaTxt.read().splitlines()
    mapaTxt.close()

    filas = len(lineas)
    columnas = len(lineas[0])

    # Creamos un arreglo de numpy para tener nuestro mapa
    mapa = np.empty((filas, columnas), dtype = object)

    # Recorremos asignando el tipo de celda correspondiente

    for fila in range(filas):
        for colum in range(columnas):
            simbolo = lineas[fila][colum]
            if simbolo == "#":
                mapa[fila][colum] = Celda(simbolo, 0)
            elif simbolo == ".":
                mapa[fila][colum] = Celda(simbolo, 4)
            else:
                mapa[fila][colum] = Celda(simbolo, 2)

    return mapa





