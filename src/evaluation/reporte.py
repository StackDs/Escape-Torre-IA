"""Resumen de un benchmark en texto plano, sin ejecutar simulaciones."""

from pathlib import Path
from statistics import fmean, stdev


NOMBRES = {
    "bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "greedy": "Greedy",
    "a_star": "A_Star", "ida_star": "IDA_Star", "genetico": "Genetico"
}


def generar_reporte(config, casos, registros):
    """Agrupa por poblacion, mapa y algoritmo. Ignora corridas no completadas.

    Los tiempos son turnos del ultimo evacuado, no tiempo de computo.
    Std es desviacion estandar muestral (n-1); necesita dos tiempos validos.
    """
    grupos = {}
    segundos = 0.0
    completadas = 0
    for caso in casos:
        registro = registros.get(caso["id"])
        if registro is None:
            continue
        clave = (caso["poblacion_inicial"], caso["mapa"], caso["algoritmo"])
        grupos.setdefault(clave, []).append(registro["resultado"])
        segundos += registro["segundos_ejecucion"]
        completadas += 1

    separador = "=" * 85
    estado = "COMPLETO" if completadas == len(casos) else "PARCIAL"
    lineas = [separador, "REPORTE DE BENCHMARKING", separador, "",
              f"Estado: {estado} | Corridas completadas: {completadas}/{len(casos)}",
              f"Modo: {config['modo']}", ""]
    parametros = config["parametros"]
    lineas.append(
        f"Parametros comunes: prob_fuego={parametros['probabilidad']} | "
        f"focos={parametros['cantidad_focos']} | "
        f"cap_pasillo={parametros['capacidad_pasillos']} | "
        f"cap_salida={parametros['capacidad_salida']}"
    )
    lineas.append(
        f"max_turnos={parametros['max_turnos']} | alpha={parametros['alpha']} | "
        f"umbral_bloqueo={parametros['umbral_bloqueo']}"
    )
    if "genetico" in config["algoritmos"]:
        lineas.append("Politica genetica: " + config.get("politica_genetica", "No indicada"))
    lineas += ["", "Mapas (orden de la configuracion):"]
    for indice, mapa in enumerate(config["mapas"], 1):
        lineas.append(f"Mapa {indice}: {Path(mapa)}")

    esperadas = len(config["semillas"])
    for poblacion in config["poblaciones"]:
        lineas += ["", separador,
                   f"Configuracion: {poblacion} agentes | {esperadas} iteraciones por mapa/algoritmo | "
                   f"k_fuego={parametros['k']}", "",
                   f"{'Mapa':<12} | {'Algoritmo':<10} | {'Superv.(%)':>10} | "
                   f"{'Media Sobrev.':>13} | {'Std Escapados':>13} | {'Min Turnos':>10} | {'Max Turnos':>10}",
                   "-" * 93]
        cobertura = []
        for indice, mapa in enumerate(config["mapas"], 1):
            for algoritmo in config["algoritmos"]:
                resultados = grupos.get((poblacion, mapa, algoritmo), [])
                tiempos = [r["turno_ultimo_evacuado"] for r in resultados
                           if r["turno_ultimo_evacuado"] is not None]
                escapados = [r.get("evacuados", r["supervivencia"] * poblacion) for r in resultados]
                supervivencia = f"{100 * fmean(r['supervivencia'] for r in resultados):.2f}%" if resultados else "N/D"
                media_sobrev = f"{fmean(escapados):.2f}" if escapados else "N/D"
                desviacion_escapados = f"{stdev(escapados):.2f}" if len(escapados) > 1 else "N/D"
                minimo = str(min(tiempos)) if tiempos else "N/D"
                maximo = str(max(tiempos)) if tiempos else "N/D"
                nombre = NOMBRES.get(algoritmo, algoritmo)
                lineas.append(
                    f"{'Mapa ' + str(indice):<12} | {nombre:<10} | {supervivencia:>10} | "
                    f"{media_sobrev:>13} | {desviacion_escapados:>13} | {minimo:>10} | {maximo:>10}"
                )
                sin_evacuados = len(resultados) - len(tiempos)
                con_limite = sum(r["motivo_termino"] == "max_turnos" for r in resultados)
                cobertura.append(
                    f"Mapa {indice} / {nombre}: {len(resultados)}/{esperadas} completas | "
                    f"tiempos validos={len(tiempos)} | sin evacuados={sin_evacuados} | "
                    f"limite de turnos={con_limite}"
                )
        lineas += ["", "Cobertura de las estadisticas:", *cobertura]

    lineas += ["", separador, f"Tiempo total: {segundos / 60:.2f} minutos", "",
               "Superv.(%): porcentaje promedio de supervivencia sobre la población inicial.",
               "Media Sobrev.: cantidad promedio de agentes que lograron escapar.",
               "Std Escapados: desviación estándar muestral (n-1) de la cantidad de agentes que escaparon.",
               "Min Turnos y Max Turnos: turnos mínimos y máximos en que evacuó el último agente con vida.",
               "Sin evacuados: supervivencia 0%; su tiempo se excluye de Min/Max Turnos.",
               "Std Escapados: N/D si hay menos de dos corridas completadas.",
               "Tiempo total: suma del tiempo de computo de corridas completas guardadas;",
               "no incluye pausas, intentos fallidos, corridas interrumpidas ni exportaciones.",
               "Los resultados sin completar o fallidos no se tratan como cero supervivencia."]
    return "\n".join(lineas) + "\n"
