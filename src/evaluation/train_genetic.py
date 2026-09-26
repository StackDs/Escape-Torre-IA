

import json
from copy import deepcopy
from pathlib import Path

from ..algorithms.Genetic.genetico import evolucionar, LIMITES_INICIALES
from ..algorithms.Genetic.politica import PoliticaGenetica


CONFIGURACION_INICIAL = {
    "tamano_poblacion": 20,
    "generaciones": 10,
    "semilla": 0,
    "probabilidad_cruce": 0.8,
    "probabilidad_mutacion": 0.2,
    "elitismo": 1,
    "tamano_torneo": 3,
    "escala_mutacion": 0.1,
    "limites": LIMITES_INICIALES
}


def evaluar_individuo(individuo, simular, escenarios, semillas):
    """Promedio de supervivencia, dando igual peso a cada ejecucion.

    simular(politica, escenario, semilla) debe construir un mapa y agentes
    nuevos y devolver enteros: evacuados, fallecidos y pendientes.
    Cada escenario debe incluir poblacion_inicial y ser serializable a JSON.
    El motor debe separar su aleatoriedad de la del genetico y asegurar
    la misma realizacion del fuego para cada escenario y semilla.
    """
    if len(escenarios) == 0 or len(semillas) == 0:
        return None

    supervivencias = []
    for escenario in escenarios:
        total = escenario.get("poblacion_inicial")
        if type(total) is not int or total <= 0:
            return None
        for semilla in semillas:
            politica = PoliticaGenetica(individuo)
            resultado = simular(politica, deepcopy(escenario), semilla)
            cantidades = []
            for nombre in ("evacuados", "fallecidos", "pendientes"):
                valor = resultado.get(nombre)
                if type(valor) is not int or valor < 0:
                    return None
                cantidades.append(valor)
            if sum(cantidades) != total:
                return None
            supervivencias.append(resultado["evacuados"] / total)

    return sum(supervivencias) / len(supervivencias)


"""Entrena y guarda parametros, aptitud, historial y condiciones usadas.

    Las semillas de evaluacion se reservan: no se ejecutan ni se usan para
    seleccionar individuos. El benchmark final debe ejecutarse por separado """

def entrenar(simular, escenarios, semillas_entrenamiento, semillas_evaluacion,
             archivo_salida, configuracion=None):
    
    if not callable(simular):
        return None
    escenarios = deepcopy(list(escenarios))
    semillas_entrenamiento = list(semillas_entrenamiento)
    semillas_evaluacion = list(semillas_evaluacion)
    if not escenarios or not semillas_entrenamiento or not semillas_evaluacion:
        return None
    for semillas in (semillas_entrenamiento, semillas_evaluacion):
        if any(type(semilla) is not int for semilla in semillas):
            return None
        if len(set(semillas)) != len(semillas):
            return None
    if set(semillas_entrenamiento) & set(semillas_evaluacion):
        return None

    opciones = deepcopy(CONFIGURACION_INICIAL)
    if configuracion is not None:
        if set(configuracion) - set(opciones):
            return None
        opciones.update(deepcopy(configuracion))
    if opciones["limites"] is None:
        opciones["limites"] = deepcopy(LIMITES_INICIALES)

    # Verificar serializacion antes de ejecutar simulaciones costosas.
    json.dumps({"escenarios": escenarios, "configuracion": opciones}, allow_nan=False)

    def evaluar(individuo):
        return evaluar_individuo(
            individuo, simular, escenarios, semillas_entrenamiento
        )

    mejor, historial = evolucionar(evaluar, **opciones)
    registro = {
        "objetivo": "supervivencia_promedio",
        "parametros": mejor.parametros(),
        "aptitud_entrenamiento": mejor.aptitud,
        "configuracion": opciones,
        "escenarios": escenarios,
        "semillas_entrenamiento": semillas_entrenamiento,
        "semillas_evaluacion_reservadas": semillas_evaluacion,
        "historial": historial
    }
    destino = Path(archivo_salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8") as archivo:
        json.dump(registro, archivo, ensure_ascii=False, indent=2, allow_nan=False)
        archivo.write("\n")
    return mejor, historial
