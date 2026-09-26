import heapq
import math


def manhattan(posicion, salida):
    return abs(posicion[0] - salida[0]) + abs(posicion[1] - salida[1])


def a_star(mapa, inicio, alpha=1.0):
    """Devuelve pasos sin el inicio, [] si ya llego o None si no hay ruta.

    Usa congestion en g y Manhattan en h. El mapa no debe cambiar
    durante la busqueda. Las capacidades se aplican al ejecutar movimientos.
    """
    if not math.isfinite(alpha) or alpha < 0:
        return None

    filas, columnas = mapa.shape
    fila_inicial, columna_inicial = inicio

    if fila_inicial < 0 or fila_inicial >= filas:
        return None
    if columna_inicial < 0 or columna_inicial >= columnas:
        return None

    celda_inicial = mapa[fila_inicial, columna_inicial]
    if celda_inicial.simbolo == "#" or celda_inicial.quemada:
        return None
    if celda_inicial.capacidad <= 0:
        return None

    # Encontrar la unica salida del mapa.
    salida = None
    for fila in range(filas):
        for columna in range(columnas):
            if mapa[fila, columna].simbolo == "E":
                if salida is not None:
                    return None
                salida = (fila, columna)

    if salida is None:
        return None
    if mapa[salida].quemada or mapa[salida].capacidad <= 0:
        return None
    if inicio == salida:
        return []

    # Direciones ortogonales
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    pendientes = []
    orden = 0
    heapq.heappush(pendientes, (manhattan(inicio, salida), orden, 0.0, inicio))
    costos = {inicio: 0.0}
    anteriores = {}

    # Procesamos las posiciones pendientes
    while len(pendientes) > 0:
        _, _, costo_actual, actual = heapq.heappop(pendientes)

        # Ignorar entradas antiguas
        if costo_actual > costos[actual]:
            continue

        # Comprobamos si se llego a la salida
        if actual == salida:
            ruta = []
            posicion = actual
            while posicion != inicio:
                ruta.append(posicion)
                posicion = anteriores[posicion]
            ruta.reverse()
            return ruta

        # Revisamos las celdas vecinas

        for cambio_fila, cambio_columna in direcciones:
            nueva_fila = actual[0] + cambio_fila
            nueva_columna = actual[1] + cambio_columna

            # Comprobamos si estamos dentro del mapa
            if nueva_fila < 0 or nueva_fila >= filas:
                continue
            if nueva_columna < 0 or nueva_columna >= columnas:
                continue

            # Ignoramos las celdas inaccesibles (quemadas o paredes)
            vecino = (nueva_fila, nueva_columna)
            celda = mapa[vecino]
            if celda.simbolo == "#" or celda.quemada:
                continue
            if celda.capacidad <= 0:
                continue

            # Calculamos el costo de movimiento en base a la capacidad
            ocupacion = len(celda.agentes)
            costo_paso = 1 + alpha * (ocupacion / celda.capacidad) ** 2
            nuevo_costo = costo_actual + costo_paso

            # Guardamos el mejor camino 
            if vecino not in costos or nuevo_costo < costos[vecino]:
                costos[vecino] = nuevo_costo
                anteriores[vecino] = actual
                # Calculamos la prioridad de A*
                prioridad = nuevo_costo + manhattan(vecino, salida)

                # Agreamos el vecino a la cola
                orden += 1 #Criterio de desempate (Procesamos la primera que fue agregada)
                heapq.heappush(pendientes, (prioridad, orden, nuevo_costo, vecino))

    return None
