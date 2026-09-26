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
                   f"{'Media':>7} | {'Std':>7} | {'Min':>5} | {'Max':>5}",
                   "-" * 85]
        cobertura = []
        for indice, mapa in enumerate(config["mapas"], 1):
            for algoritmo in config["algoritmos"]:
                resultados = grupos.get((poblacion, mapa, algoritmo), [])
                tiempos = [r["turno_ultimo_evacuado"] for r in resultados
                           if r["turno_ultimo_evacuado"] is not None]
                supervivencia = f"{100 * fmean(r['supervivencia'] for r in resultados):.2f}%" if resultados else "N/D"
                media = f"{fmean(tiempos):.2f}" if tiempos else "N/D"
                desviacion = f"{stdev(tiempos):.2f}" if len(tiempos) > 1 else "N/D"
                minimo = str(min(tiempos)) if tiempos else "N/D"
                maximo = str(max(tiempos)) if tiempos else "N/D"
                nombre = NOMBRES.get(algoritmo, algoritmo)
                lineas.append(
                    f"{'Mapa ' + str(indice):<12} | {nombre:<10} | {supervivencia:>10} | "
                    f"{media:>7} | {desviacion:>7} | {minimo:>5} | {maximo:>5}"
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
               "Media, Std, Min y Max: turnos del ultimo evacuado de cada corrida.",
               "Sin evacuados: supervivencia 0%; su tiempo se excluye, no se reemplaza por cero.",
               "Std: desviacion estandar muestral (n-1). N/D si hay menos de dos tiempos.",
               "Las corridas al limite conservan su tiempo observado si tuvieron evacuados.",
               "Tiempo total: suma del tiempo de computo de corridas completas guardadas;",
               "no incluye pausas, intentos fallidos, corridas interrumpidas ni exportaciones.",
               "Los resultados sin completar o fallidos no se tratan como cero supervivencia."]
    return "\n".join(lineas) + "\n"
