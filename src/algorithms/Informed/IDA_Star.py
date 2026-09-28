from collections import deque
import math


def manhattan(posicion, salida):
    return abs(posicion[0] - salida[0]) + abs(posicion[1] - salida[1])


def ida_star(mapa, inicio, alpha=1.0):
    """IDA* con congestion, Manhattan y mejores costos por umbral.

    Devuelve pasos sin el inicio, [] si ya llego o None si no hay ruta.
    El mapa no debe cambiar durante la busqueda. Puede repetir muchas
    expansiones al aumentar el umbral, especialmente con costos variables.
    La tabla por umbral usa memoria O(celdas), ademas de la pila del camino.
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

    # Preparar una vez el grafo alcanzable en este mapa estable con BFS.
    # Evita iterar umbrales cuando el fuego o los muros ya separaron la salida
    # y calcula la cota inferior topologica exacta distancias[salida] en O(V+E).
    vecinos = {}
    cola = deque([(inicio, 0)])
    distancias = {inicio: 0}
    while cola:
        actual, dist = cola.popleft()
        vecinos[actual] = []
        for cambio_fila, cambio_columna in direcciones:
            vecino = (actual[0] + cambio_fila, actual[1] + cambio_columna)
            if not (0 <= vecino[0] < filas and 0 <= vecino[1] < columnas):
                continue
            celda = mapa[vecino]
            if celda.simbolo == "#" or celda.quemada or celda.capacidad <= 0:
                continue
            costo_paso = 1 + alpha * (len(celda.agentes) / celda.capacidad) ** 2
            vecinos[actual].append((vecino, costo_paso, manhattan(vecino, salida)))
            if vecino not in distancias:
                distancias[vecino] = dist + 1
                cola.append((vecino, dist + 1))
        # Ordenar ramas por f estimado (costo_paso + heuristica) para explorar primero
        # los caminos directos a la salida y evitar ramas ciegas masivas en DFS.
        vecinos[actual].sort(key=lambda item: item[1] + item[2])
    if salida not in distancias:
        return None

    # Cota inferior admisible: cualquier camino tiene al menos distancias[salida] pasos,
    # y cada paso cuesta al menos 1.0 (costo unitario base + congestion >= 1.0).
    limite = max(manhattan(inicio, salida), distancias[salida])

    while True:
        siguiente_limite = math.inf
        ruta = [inicio]
        en_ruta = {inicio}
        # No repetir una celda con igual o mayor costo dentro del mismo umbral.
        # Si llegamos mas barato, la reabrimos. Reiniciar al cambiar el umbral:
        # las ramas cortadas antes necesitan explorarse con el nuevo presupuesto.
        mejores_costos = {inicio: 0.0}

        # Cada marco guarda: posicion, costo g y proxima direccion a revisar, una pila explicita evita el limite de recursion en rutas largas.
        pila = [[inicio, 0.0, 0]]

        while len(pila) > 0:
            actual, costo_actual, direccion = pila[-1]

            if actual == salida:
                return ruta[1:]

            if direccion == len(vecinos[actual]):
                pila.pop()
                en_ruta.remove(actual)
                ruta.pop()
                continue

            # Guardar donde continuar cuando volvamos a esta posicion.
            pila[-1][2] += 1
            vecino, costo_paso, heuristica = vecinos[actual][direccion]

            # Evitar ciclos solo en el camino actual. Otras ramas pueden alcanzar la misma celda con un costo diferente.
            if vecino in en_ruta:
                continue

            nuevo_costo = costo_actual + costo_paso
            if nuevo_costo >= mejores_costos.get(vecino, math.inf):
                continue
            estimacion = nuevo_costo + heuristica

            if estimacion > limite:
                siguiente_limite = min(siguiente_limite, estimacion)
                continue

            mejores_costos[vecino] = nuevo_costo
            ruta.append(vecino)
            en_ruta.add(vecino)
            pila.append([vecino, nuevo_costo, 0])

        if siguiente_limite == math.inf:
            return None

        # Usar el menor valor que excedio el umbral anterior con un avance minimo
        # de 1.0 para evitar la explosion combinatoria por deltas infinitesimales.
        limite = max(siguiente_limite, limite + 1.0)
