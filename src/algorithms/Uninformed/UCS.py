import heapq

def ucs(mapa, inicio, alpha=1.0):
    if alpha < 0:
        return None

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

    # Cola de prioridad: (costo acumulado, orden de llegada, posicion).
    pendientes = []
    orden = 0
    heapq.heappush(pendientes, (0.0, orden, inicio))

    # Menor costo encontrado para llegar a cada posicion.
    costos = {}
    costos[inicio] = 0.0

    # Guarda desde donde llegamos a cada posicion.
    anteriores = {}

    direcciones = [
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1)
    ]

    while len(pendientes) > 0:
        costo_actual, _, actual = heapq.heappop(pendientes)

        # Ignorar una entrada antigua si ya encontramo una forma mas barata de llegar a esta posicion.
        if costo_actual > costos[actual]:
            continue

        fila, columna = actual
        celda = mapa[fila, columna]

        # Encontramos la salida con su menor costo acumulado.
        if celda.simbolo == "E":
            ruta = []
            posicion = actual

            while posicion != inicio:
                ruta.append(posicion)
                posicion = anteriores[posicion]

            ruta.reverse()
            return ruta

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

            # Calcular el costo de entrar a la celda vecina.
            ocupacion = len(celda_vecina.agentes)
            capacidad = celda_vecina.capacidad

            costo_paso = 1 + alpha * (ocupacion / capacidad) ** 2
            nuevo_costo = costo_actual + costo_paso

            # Actualizar si es la primera ruta al vecino o si encontramos una ruta mas barata.
            if vecino not in costos or nuevo_costo < costos[vecino]:
                costos[vecino] = nuevo_costo
                anteriores[vecino] = actual

                orden += 1
                heapq.heappush(
                    pendientes,
                    (nuevo_costo, orden, vecino)
                )

    return None