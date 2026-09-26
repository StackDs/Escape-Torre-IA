from collections import deque


def bfs(mapa, inicio):
    filas, columnas = mapa.shape
    fila_inicial, columna_inicial = inicio

    # Comprobar que el inicio este dentro del mapa.
    if fila_inicial < 0 or fila_inicial >= filas:
        return None

    if columna_inicial < 0 or columna_inicial >= columnas:
        return None

    celda_inicial = mapa[fila_inicial, columna_inicial]

    if celda_inicial.simbolo == "#" or celda_inicial.quemada:
        return None
    if celda_inicial.capacidad <= 0:
        return None

    # Posiciones pendientes de explorar.
    pendientes = deque()
    pendientes.append(inicio)

    # Posiciones que ya descubrimos.
    visitados = set()
    visitados.add(inicio)

    # Guarda desde que posicion llegamos a cada celda.
    anteriores = {}

    # Arriba, abajo, izquierda y derecha.
    direcciones = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1)
    ]

    while len(pendientes) > 0:
        actual = pendientes.popleft()

        fila, columna = actual
        celda = mapa[fila, columna]

        # Encontramos la salida: reconstruimos el camino.
        if celda.simbolo == "E":
            ruta = []
            posicion = actual

            while posicion != inicio:
                ruta.append(posicion)
                posicion = anteriores[posicion]

            ruta.reverse()
            return ruta

        # Revisar las cuatro posiciones vecinas.
        for cambio_fila, cambio_columna in direcciones:
            nueva_fila = fila + cambio_fila
            nueva_columna = columna + cambio_columna

            if nueva_fila < 0 or nueva_fila >= filas:
                continue

            if nueva_columna < 0 or nueva_columna >= columnas:
                continue

            vecino = (nueva_fila, nueva_columna)
            celda_vecina = mapa[nueva_fila, nueva_columna]

            if celda_vecina.simbolo == "#":
                continue

            if celda_vecina.quemada:
                continue
            if celda_vecina.capacidad <= 0:
                continue

            if vecino in visitados:
                continue

            visitados.add(vecino)
            anteriores[vecino] = actual
            pendientes.append(vecino)

    # Exploramos todo lo alcanzable sin encontrar la salida.
    return None
