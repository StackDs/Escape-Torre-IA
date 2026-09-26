import math


def manhattan(posicion, salida):
    return abs(posicion[0] - salida[0]) + abs(posicion[1] - salida[1])


def ida_star(mapa, inicio, alpha=1.0):
    """IDA* con congestion y Manhattan, sin recursion de Python.

    Devuelve pasos sin el inicio, [] si ya llego o None si no hay ruta.
    El mapa no debe cambiar durante la busqueda. Puede repetir muchas
    expansiones al aumentar el umbral, especialmente con costos variables.
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

    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    limite = manhattan(inicio, salida)

    while True:
        siguiente_limite = math.inf
        ruta = [inicio]
        en_ruta = {inicio}

        # Cada marco guarda: posicion, costo g y proxima direccion a revisar, una pila explicita evita el limite de recursion en rutas largas.
        pila = [[inicio, 0.0, 0]]

        while len(pila) > 0:
            actual, costo_actual, direccion = pila[-1]

            if actual == salida:
                return ruta[1:]

            if direccion == len(direcciones):
                pila.pop()
                en_ruta.remove(actual)
                ruta.pop()
                continue

            # Guardar donde continuar cuando volvamos a esta posicion.
            pila[-1][2] += 1
            cambio_fila, cambio_columna = direcciones[direccion]
            nueva_fila = actual[0] + cambio_fila
            nueva_columna = actual[1] + cambio_columna

            if nueva_fila < 0 or nueva_fila >= filas:
                continue
            if nueva_columna < 0 or nueva_columna >= columnas:
                continue

            vecino = (nueva_fila, nueva_columna)
            celda = mapa[vecino]
            if celda.simbolo == "#" or celda.quemada:
                continue
            if celda.capacidad <= 0:
                continue

            # Evitar ciclos solo en el camino actual. Otras ramas pueden alcanzar la misma celda con un costo diferente.
            if vecino in en_ruta:
                continue

            ocupacion = len(celda.agentes)
            costo_paso = 1 + alpha * (ocupacion / celda.capacidad) ** 2
            nuevo_costo = costo_actual + costo_paso
            estimacion = nuevo_costo + manhattan(vecino, salida)

            if estimacion > limite:
                siguiente_limite = min(siguiente_limite, estimacion)
                continue

            ruta.append(vecino)
            en_ruta.add(vecino)
            pila.append([vecino, nuevo_costo, 0])

        if siguiente_limite == math.inf:
            return None

        # Usar el menor valor que excedio el umbral anterior.
        limite = siguiente_limite
