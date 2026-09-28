"""Resumen de un benchmark en texto plano, sin ejecutar simulaciones."""

from pathlib import Path
from statistics import fmean, stdev


NOMBRES = {
    "bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "greedy": "Greedy",
    "a_star": "A_Star", "ida_star": "IDA_Star", "genetico": "Genetico"
}


def generar_reporte(config, casos, registros):
    """Agrupa por poblacion, mapa y algoritmo. Ignora runs no completados.

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
        grupos.setdefault(clave, []).append(registro)
        segundos += registro["segundos_ejecucion"]
        completadas += 1

    separador = "=" * 148
    estado = "COMPLETO" if completadas == len(casos) else "PARCIAL"
    lineas = [separador, "REPORTE DE BENCHMARKING", separador, "",
              f"Estado: {estado} | Runs completados: {completadas}/{len(casos)}",
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
        lineas += [
            "", separador,
            f"Configuracion: {poblacion} agentes | {esperadas} iteraciones por mapa/algoritmo | "
            f"k_fuego={parametros['k']}", "",
            "TABLA 1: SUPERVIVENCIA Y TIEMPOS DE EVACUACIÓN (TURNOS)",
            f"{'Mapa':<10} | {'Algoritmo':<10} | {'Superv.(%)':>10} | "
            f"{'Media Sobrev.':>13} | {'Std Escapados':>13} | "
            f"{'Min Escap.':>10} | {'Max Escap.':>10} | "
            f"{'Media Turnos':>12} | {'Std Turnos':>10} | "
            f"{'Min Turnos':>10} | {'Max Turnos':>10}",
            "-" * 148
        ]
        cobertura = []
        filas_operativas = []
        for indice, mapa in enumerate(config["mapas"], 1):
            for algoritmo in config["algoritmos"]:
                items = grupos.get((poblacion, mapa, algoritmo), [])
                resultados = [it["resultado"] for it in items]
                segundos_cpu = [it.get("segundos_ejecucion", 0.0) for it in items]
                tiempos = [r["turno_ultimo_evacuado"] for r in resultados
                           if r["turno_ultimo_evacuado"] is not None]
                escapados = [r.get("evacuados", r["supervivencia"] * poblacion) for r in resultados]
                supervivencia = f"{100 * fmean(r['supervivencia'] for r in resultados):.2f}%" if resultados else "N/D"
                media_sobrev = f"{fmean(escapados):.2f}" if escapados else "N/D"
                desviacion_escapados = f"{stdev(escapados):.2f}" if len(escapados) > 1 else "N/D"
                min_escapados = str(min(escapados)) if escapados else "N/D"
                max_escapados = str(max(escapados)) if escapados else "N/D"
                media_turnos = f"{fmean(tiempos):.2f}" if tiempos else "N/D"
                desviacion_turnos = f"{stdev(tiempos):.2f}" if len(tiempos) > 1 else "N/D"
                minimo = str(min(tiempos)) if tiempos else "N/D"
                maximo = str(max(tiempos)) if tiempos else "N/D"
                nombre = NOMBRES.get(algoritmo, algoritmo)
                mapa_tag = f"Mapa {indice}"
                lineas.append(
                    f"{mapa_tag:<10} | {nombre:<10} | {supervivencia:>10} | "
                    f"{media_sobrev:>13} | {desviacion_escapados:>13} | "
                    f"{min_escapados:>10} | {max_escapados:>10} | "
                    f"{media_turnos:>12} | {desviacion_turnos:>10} | "
                    f"{minimo:>10} | {maximo:>10}"
                )

                # Tabla 2: Dinámica Operativa y Costo Computacional
                media_esperas = f"{fmean(r['esperas'] for r in resultados):.1f}" if resultados else "N/D"
                media_planif = f"{fmean(r['planificaciones'] for r in resultados):.1f}" if resultados else "N/D"
                media_movim = f"{fmean(r['movimientos'] for r in resultados):.1f}" if resultados else "N/D"
                cpu_medio = f"{fmean(segundos_cpu):.2f}" if segundos_cpu else "N/D"
                filas_operativas.append(
                    f"{mapa_tag:<10} | {nombre:<10} | {media_esperas:>13} | "
                    f"{media_planif:>13} | {media_movim:>12} | {cpu_medio:>13}"
                )

                sin_evacuados = len(resultados) - len(tiempos)
                con_limite = sum(r["motivo_termino"] == "max_turnos" for r in resultados)
                cobertura.append(
                    f"Mapa {indice} / {nombre}: {len(resultados)}/{esperadas} completas | "
                    f"tiempos validos={len(tiempos)} | min/max escapados={min_escapados}/{max_escapados} | "
                    f"sin evacuados={sin_evacuados} | limite de turnos={con_limite}"
                )

        lineas += [
            "",
            "TABLA 2: DINÁMICA OPERATIVA Y COSTO COMPUTACIONAL (HIPÓTESIS H1, H2, H3)",
            f"{'Mapa':<10} | {'Algoritmo':<10} | {'Media Esperas':>13} | {'Media Planif.':>13} | {'Media Movim.':>12} | {'CPU medio (s)':>13}",
            "-" * 86,
            *filas_operativas
        ]

        lineas += ["", "Cobertura de las estadisticas:", *cobertura]

    lineas += [
        "", separador, f"Tiempo total: {segundos / 60:.2f} minutos", "",
        "Tabla 1 (Supervivencia y Tiempos de Evacuación):",
        "  Superv.(%): porcentaje promedio de supervivencia sobre la población inicial.",
        "  Media Sobrev.: cantidad promedio de agentes que lograron escapar.",
        "  Std Escapados: desviación estándar muestral (n-1) de la cantidad de evacuados.",
        "  Min Escap. y Max Escap.: cantidad mínima y máxima de agentes evacuados en un run.",
        "  Media Turnos y Std Turnos: media y desviación estándar del turno del último evacuado (m tiempos válidos).",
        "  Min Turnos y Max Turnos: turno mínimo y máximo en que evacuó el último agente con vida.",
        "",
        "Tabla 2 (Dinámica Operativa y Costo Computacional):",
        "  Media Esperas: promedio de turnos de inmovilidad acumulados por congestión o falta de cupo (valida H1).",
        "  Media Planif.: promedio de llamadas de replanificación por agente a los algoritmos (valida H1 y H2).",
        "  Media Movim.: promedio de pasos ortogonales ejecutados con éxito (valida H2).",
        "  CPU medio (s): promedio de segundos de procesador insumidos por simulación completa (valida H3).",
        "",
        "Notas metodológicas:",
        "  Sin evacuados: supervivencia 0%; su tiempo se excluye del cómputo temporal (N/D).",
        "  Std: N/D si hay menos de dos observaciones válidas.",
        "  Tiempo total: suma del tiempo de computo de runs completos guardados;",
        "  no incluye pausas, intentos fallidos, runs interrumpidos ni exportaciones.",
        "  Los resultados sin completar o fallidos no se tratan como cero supervivencia."
    ]
    return "\n".join(lineas) + "\n"
