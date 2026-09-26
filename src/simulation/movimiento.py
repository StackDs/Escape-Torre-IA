
from ..models.agente import State


def resolver_movimientos(mapa, agentes, azar):
    """Devuelve IDs aceptados sin cambiar agentes ni ocupacion.

    Cada agente propone el primer paso de su ruta. El espacio disponible
    se mide antes de mover a nadie; las salidas no liberan cupos este turno.
    """
    filas, columnas = mapa.shape
    solicitudes = {}
    for agente in sorted(agentes, key=lambda persona: persona.id_agente):
        if agente.estado not in (State.ACTIVO, State.ESPERANDO):
            continue
        destino = agente.siguiente_posicion()
        if destino is None:
            continue
        fila, columna = destino
        if not (0 <= fila < filas and 0 <= columna < columnas):
            continue
        distancia = abs(fila - agente.fila) + abs(columna - agente.columna)
        celda = mapa[fila, columna]
        if distancia != 1 or celda.simbolo == "#" or celda.quemada:
            continue
        destino = (fila, columna)
        if destino not in solicitudes:
            solicitudes[destino] = []
        solicitudes[destino].append(agente.id_agente)

    aceptados = set()
    for destino in sorted(solicitudes):
        celda = mapa[destino]
        espacios = max(0, celda.capacidad - len(celda.agentes))
        candidatos = solicitudes[destino]
        if len(candidatos) > espacios:
            ganadores = azar.sample(candidatos, espacios)
        else:
            ganadores = candidatos
        aceptados.update(ganadores)
    return aceptados


def aplicar_movimientos(mapa, agentes, aceptados, turno):
    # Actualiza posiciones, celdas y contadores una sola vez por agente
    movimientos = []
    for agente in agentes:
        if agente.estado not in (State.ACTIVO, State.ESPERANDO):
            continue
        if agente.id_agente in aceptados:
            movimientos.append((agente, agente.siguiente_posicion()))
        else:
            agente.estado = State.ESPERANDO
            agente.esperas += 1
            if agente.siguiente_posicion() is not None:
                agente.turnos_bloqueado += 1
            else:
                # No tener una ruta no es un rechazo por capacidad
                agente.turnos_bloqueado = 0

    # Primero retirar todos los movimientos aprobados de sus origenes
    for agente, destino in movimientos:
        mapa[agente.fila, agente.columna].agentes.remove(agente)

    # Luego aplicar destinos. No resolver nuevas admisiones en esta fase
    for agente, destino in movimientos:
        agente.fila, agente.columna = destino
        agente.ruta.pop(0)
        agente.movimientos += 1
        agente.turnos_bloqueado = 0
        celda = mapa[agente.fila, agente.columna]
        if celda.simbolo == "E":
            agente.estado = State.EVACUADO
            agente.turno_evacuacion = turno
            agente.borrar_ruta()
        else:
            agente.estado = State.ACTIVO
            celda.agentes.append(agente)
