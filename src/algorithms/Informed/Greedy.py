import heapq


def manhattan(posicion, salida):
    return abs(posicion[0] - salida[0]) + abs(posicion[1] - salida[1])


def greedy(mapa, inicio):
    """Busca usando solo Manhattan; no garantiza una ruta de menor costo.

    Devuelve pasos sin el inicio, [] si ya llego o None si no hay ruta.
    El mapa no debe cambiar durante la busqueda.
    """
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

    # Direcciones ortogonales

    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    pendientes = []
    orden = 0
    heapq.heappush(pendientes, (manhattan(inicio, salida), orden, inicio))
    visitados = {inicio}
    anteriores = {}

    # Extraemos la posicion mas prometedora
    while len(pendientes) > 0:
        _, _, actual = heapq.heappop(pendientes)

        # Comprobacion de salida
        if actual == salida:
            ruta = []
            posicion = actual
            while posicion != inicio:
                ruta.append(posicion)
                posicion = anteriores[posicion]
            ruta.reverse()
            return ruta

        # Generamos los vecinos
        for cambio_fila, cambio_columna in direcciones:
            nueva_fila = actual[0] + cambio_fila
            nueva_columna = actual[1] + cambio_columna

            # Verificacion de limites 
            if nueva_fila < 0 or nueva_fila >= filas:
                continue
            if nueva_columna < 0 or nueva_columna >= columnas:
                continue

            # Verificacion de celda
            vecino = (nueva_fila, nueva_columna)
            celda = mapa[vecino]
            if celda.simbolo == "#" or celda.quemada:
                continue
            if celda.capacidad <= 0:
                continue

            if vecino in visitados:
                continue

            visitados.add(vecino)
            anteriores[vecino] = actual

            # Agregamos a la cola basados en manhattan
            orden += 1
            heapq.heappush(pendientes, (manhattan(vecino, salida), orden, vecino))

    return None
