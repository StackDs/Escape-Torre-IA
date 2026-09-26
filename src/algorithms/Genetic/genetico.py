import math
import random

from .individuo import Individuo


# Rangos iniciales para desarrollo; deben fijarse antes del entrenamiento final.
LIMITES_INICIALES = {
    "peso_congestion": (0.0, 10.0),
    "peso_riesgo": (0.0, 10.0),
    "umbral_bloqueo": (1, 10)
}


def validar_limites(limites):
    if set(limites) != set(LIMITES_INICIALES):
        raise ValueError("Los limites deben definir exactamente los tres genes.")
    for nombre, rango in limites.items():
        minimo, maximo = rango
        if not math.isfinite(minimo) or not math.isfinite(maximo):
            raise ValueError("Los limites deben ser finitos.")
        if minimo > maximo or minimo < 0:
            raise ValueError("Rango de parametros invalido.")
        if nombre == "umbral_bloqueo":
            if type(minimo) is not int or type(maximo) is not int or minimo < 1:
                raise ValueError("Los limites del umbral deben ser enteros positivos.")


def crear_individuo(azar, limites):
    return Individuo(
        azar.uniform(*limites["peso_congestion"]),
        azar.uniform(*limites["peso_riesgo"]),
        azar.randint(*limites["umbral_bloqueo"])
    )


def seleccionar_torneo(poblacion, azar, tamano_torneo):
    participantes = azar.sample(poblacion, tamano_torneo)
    return max(participantes, key=lambda individuo: individuo.aptitud)


def cruzar(padre_1, padre_2, azar):
    # Cruce uniforme: cada gen proviene de uno de los padres.
    return Individuo(
        azar.choice([padre_1.peso_congestion, padre_2.peso_congestion]),
        azar.choice([padre_1.peso_riesgo, padre_2.peso_riesgo]),
        azar.choice([padre_1.umbral_bloqueo, padre_2.umbral_bloqueo])
    )


def mutar(individuo, azar, limites, probabilidad, escala):
    # Devolver una copia evita modificar padres o elites.
    hijo = individuo.copiar()
    hijo.aptitud = None
    for nombre in ("peso_congestion", "peso_riesgo"):
        if azar.random() < probabilidad:
            minimo, maximo = limites[nombre]
            valor = getattr(hijo, nombre)
            valor += azar.gauss(0, escala * (maximo - minimo))
            setattr(hijo, nombre, max(minimo, min(maximo, valor)))

    if azar.random() < probabilidad:
        minimo, maximo = limites["umbral_bloqueo"]
        valor = hijo.umbral_bloqueo + azar.choice([-1, 1])
        hijo.umbral_bloqueo = max(minimo, min(maximo, valor))
    return hijo


def evolucionar(evaluar, tamano_poblacion=20, generaciones=10, semilla=0,
                probabilidad_cruce=0.8, probabilidad_mutacion=0.2,
                elitismo=1, tamano_torneo=3, escala_mutacion=0.1,
                limites=None):
    """Optimiza una aptitud de supervivencia entre 0 y 1.

    evaluar(individuo) debe usar los mismos escenarios en todas las llamadas.
    generaciones cuenta las poblaciones evaluadas, incluida la inicial.
    Devuelve (mejor_individuo, historial).
    """
    if limites is None:
        limites = LIMITES_INICIALES.copy()
    validar_limites(limites)
    if type(tamano_poblacion) is not int or tamano_poblacion < 2:
        raise ValueError("Se requieren al menos dos individuos.")
    if type(generaciones) is not int or generaciones < 1:
        raise ValueError("Se requiere al menos una generacion.")
    if type(elitismo) is not int or not 1 <= elitismo < tamano_poblacion:
        raise ValueError("El elitismo debe estar entre 1 y poblacion - 1.")
    if type(tamano_torneo) is not int or not 1 <= tamano_torneo <= tamano_poblacion:
        raise ValueError("El torneo debe caber en la poblacion.")
    for valor in (probabilidad_cruce, probabilidad_mutacion):
        if not math.isfinite(valor) or not 0 <= valor <= 1:
            raise ValueError("Las probabilidades deben estar entre 0 y 1.")
    if not math.isfinite(escala_mutacion) or escala_mutacion <= 0:
        raise ValueError("La escala de mutacion debe ser finita y positiva.")

    # Este generador solo controla la evolucion, nunca el fuego o los agentes.
    azar = random.Random(semilla)
    poblacion = []
    for _ in range(tamano_poblacion):
        poblacion.append(crear_individuo(azar, limites))
    historial = []

    for generacion in range(generaciones):
        for individuo in poblacion:
            aptitud = float(evaluar(individuo.copiar()))
            if not math.isfinite(aptitud) or not 0 <= aptitud <= 1:
                raise ValueError("La aptitud debe ser una supervivencia entre 0 y 1.")
            individuo.aptitud = aptitud

        poblacion.sort(key=lambda individuo: individuo.aptitud, reverse=True)
        promedio = sum(individuo.aptitud for individuo in poblacion) / tamano_poblacion
        historial.append({
            "generacion": generacion,
            "mejor_aptitud": poblacion[0].aptitud,
            "aptitud_promedio": promedio,
            "mejores_parametros": poblacion[0].parametros()
        })
        if generacion == generaciones - 1:
            break

        nueva_poblacion = []
        for indice in range(elitismo):
            nueva_poblacion.append(poblacion[indice].copiar())

        while len(nueva_poblacion) < tamano_poblacion:
            padre_1 = seleccionar_torneo(poblacion, azar, tamano_torneo)
            padre_2 = seleccionar_torneo(poblacion, azar, tamano_torneo)
            if azar.random() < probabilidad_cruce:
                hijo = cruzar(padre_1, padre_2, azar)
            else:
                hijo = padre_1.copiar()
            hijo = mutar(hijo, azar, limites, probabilidad_mutacion, escala_mutacion)
            nueva_poblacion.append(hijo)
        poblacion = nueva_poblacion

    return poblacion[0].copiar(), historial
