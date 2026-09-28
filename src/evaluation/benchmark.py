
import argparse
import csv
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..simulation.motor import MotorSimulacion, VALORES_INICIALES, simular
from ..simulation.politicas import BUSQUEDAS
from ..algorithms.Genetic.individuo import Individuo
from ..algorithms.Genetic.politica import PoliticaGenetica
from .reporte import generar_reporte


RAIZ = Path(__file__).resolve().parents[2]
CAMPOS_METRICAS = [
    "evacuados", "fallecidos", "pendientes", "supervivencia", "turnos_ejecutados",
    "turno_ultimo_evacuado", "motivo_termino", "movimientos", "esperas", "planificaciones"
]


def huella(valor):
    texto = json.dumps(valor, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def huella_archivo(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()



def guardar_texto(ruta, texto):   
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    with temporal.open("w", encoding="utf-8", newline="") as archivo:
        archivo.write(texto)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ruta)


def guardar_json(ruta, valor):
    guardar_texto(ruta, json.dumps(valor, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def lista_unica(valores, nombre):
    if not isinstance(valores, list) or not valores:
        raise ValueError(nombre + " debe ser una lista no vacia.")
    if len(set(valores)) != len(valores):
        raise ValueError(nombre + " contiene duplicados.")


def preparar_configuracion(configuracion):
    """Las rutas de mapas y politica se resuelven desde la raiz del proyecto."""
    config = deepcopy(configuracion)
    permitidos = {"modo", "mapas", "poblaciones", "semillas", "algoritmos", "parametros", "politica_genetica"}
    if not isinstance(config, dict) or set(config) - permitidos:
        raise ValueError("Configuracion de benchmark invalida.")
    if config.get("modo") not in ("piloto", "final"):
        raise ValueError("El modo debe ser piloto o final.")
    for nombre in ("mapas", "poblaciones", "semillas", "algoritmos"):
        lista_unica(config.get(nombre), nombre)
    if any(type(n) is not int or n <= 0 for n in config["poblaciones"]):
        raise ValueError("Las poblaciones deben ser enteros positivos.")
    if any(type(n) is not int for n in config["semillas"]):
        raise ValueError("Las semillas deben ser enteras.")
    if config["modo"] == "final" and len(config["semillas"]) < 80:
        raise ValueError("El benchmark final requiere al menos 80 semillas por configuracion.")
    for algoritmo in config["algoritmos"]:
        if algoritmo not in BUSQUEDAS and algoritmo != "genetico":
            raise ValueError("Algoritmo desconocido: " + str(algoritmo))

    parametros = config.get("parametros", {})
    if not isinstance(parametros, dict) or set(parametros) - set(VALORES_INICIALES):
        raise ValueError("parametros solo admite los valores comunes del motor.")
    config["parametros"] = dict(VALORES_INICIALES, **parametros)
    mapas = []
    for mapa in config["mapas"]:
        if not isinstance(mapa, str):
            raise ValueError("Cada mapa debe ser una ruta de texto.")
        ruta = (RAIZ / mapa).resolve()
        if not ruta.is_file():
            raise ValueError("No existe el mapa: " + str(ruta))
        mapas.append(str(ruta))
    lista_unica(mapas, "mapas resueltos")
    config["mapas"] = mapas

    politica = None
    if "genetico" in config["algoritmos"]:
        archivo = config.get("politica_genetica")
        if not isinstance(archivo, str):
            raise ValueError("genetico requiere politica_genetica con el JSON entrenado.")
        ruta = (RAIZ / archivo).resolve()
        if not ruta.is_file():
            raise ValueError("Falta la politica entrenada: " + str(ruta))
        registro = json.loads(ruta.read_text(encoding="utf-8"))
        entrenamiento = registro.get("semillas_entrenamiento")
        if not isinstance(entrenamiento, list) or not entrenamiento:
            raise ValueError("La politica debe registrar sus semillas de entrenamiento.")
        if set(entrenamiento) & set(config["semillas"]):
            raise ValueError("El benchmark no puede usar semillas de entrenamiento del genetico.")
        politica = PoliticaGenetica(Individuo(**registro["parametros"]))
        config["politica_genetica"] = str(ruta)

    # Validar que todos los escenarios se pueden inicializar, sin ejecutar busquedas.
    for mapa in mapas:
        for poblacion in config["poblaciones"]:
            escenario = dict(config["parametros"], mapa=mapa, poblacion_inicial=poblacion)
            MotorSimulacion("bfs", escenario, config["semillas"][0])
    return config, politica


def construir_casos(config):
    casos = []
    contador = 0
    for mapa in config["mapas"]:
        for poblacion in config["poblaciones"]:
            for semilla in config["semillas"]:
                for algoritmo in config["algoritmos"]:
                    caso = {
                        "id": contador,
                        "mapa": mapa,
                        "poblacion_inicial": poblacion,
                        "semilla": semilla,
                        "algoritmo": algoritmo,
                    }
                    contador += 1
                    casos.append(caso)
    return casos


def construir_identidad(config):
    # Incluye cambios sin commit y evita mezclar resultados de distintas versiones.
    fuentes = {}
    for ruta in sorted((RAIZ / "src").rglob("*.py")):
        fuentes[str(ruta.relative_to(RAIZ))] = huella_archivo(ruta)
    identidad = {
        "formato": 1,
        "configuracion": config,
        "mapas_sha256": {mapa: huella_archivo(mapa) for mapa in config["mapas"]},
        "fuentes_sha256": fuentes,
        "python": platform.python_version(),
        "numpy": np.__version__
    }
    if "genetico" in config["algoritmos"]:
        identidad["politica_sha256"] = huella_archivo(config["politica_genetica"])
    return identidad


def validar_resultado(resultado, caso, max_turnos):
    if not isinstance(resultado, dict) or any(c not in resultado for c in CAMPOS_METRICAS):
        raise ValueError("El simulador no devolvio todas las metricas requeridas.")
    for campo in ("evacuados", "fallecidos", "pendientes", "turnos_ejecutados",
                  "movimientos", "esperas", "planificaciones"):
        if type(resultado[campo]) is not int or resultado[campo] < 0:
            raise ValueError("Metrica invalida: " + campo)
    n = caso["poblacion_inicial"]
    if sum(resultado[c] for c in ("evacuados", "fallecidos", "pendientes")) != n:
        raise ValueError("El resultado no conserva la poblacion inicial.")
    if not math.isclose(resultado["supervivencia"], resultado["evacuados"] / n):
        raise ValueError("La supervivencia no coincide con los evacuados.")
    turnos = resultado["turnos_ejecutados"]
    if not 1 <= turnos <= max_turnos:
        raise ValueError("Cantidad de turnos fuera del limite.")
    ultimo = resultado["turno_ultimo_evacuado"]
    if resultado["evacuados"] == 0:
        if ultimo is not None:
            raise ValueError("Sin evacuados, el turno final debe ser None.")
    elif type(ultimo) is not int or not 1 <= ultimo <= turnos:
        raise ValueError("Turno del ultimo evacuado invalido.")
    if resultado["pendientes"]:
        if resultado["motivo_termino"] != "max_turnos" or turnos != max_turnos:
            raise ValueError("Un resultado con pendientes debe alcanzar el limite de turnos.")
    elif resultado["motivo_termino"] != "sin_agentes_pendientes":
        raise ValueError("Motivo de termino inconsistente.")


def exportar_csv(destino, casos, registros):
    campos = ["id", "mapa", "poblacion_inicial", "semilla", "algoritmo"]
    campos += CAMPOS_METRICAS + ["segundos_ejecucion"]
    texto = io.StringIO(newline="")
    escritor = csv.DictWriter(texto, fieldnames=campos)
    escritor.writeheader()
    for caso in casos:
        registro = registros.get(caso["id"])
        if registro is not None:
            fila = dict(caso, **registro["resultado"])
            fila["segundos_ejecucion"] = registro["segundos_ejecucion"]
            escritor.writerow({campo: fila[campo] for campo in campos})
    guardar_texto(destino / "resultados.csv", texto.getvalue())


def exportar_txt(destino, config, casos, registros):
    guardar_texto(Path(destino) / "reporte_benchmark.txt", generar_reporte(config, casos, registros))


def cargar_registros(destino, casos, firma, max_turnos):
    registros = {}
    for caso in casos:
        archivo = Path(destino) / "runs" / f"{caso['id']}.json"
        if archivo.exists():
            registro = json.loads(archivo.read_text(encoding="utf-8"))
            if registro.get("firma") != firma or registro.get("caso") != caso:
                raise ValueError("Punto de guardado inconsistente: " + str(archivo))
            validar_resultado(registro["resultado"], caso, max_turnos)
            segundos = registro.get("segundos_ejecucion")
            if not isinstance(segundos, (int, float)) or not math.isfinite(segundos) or segundos < 0:
                raise ValueError("Duracion invalida en el punto de guardado: " + str(archivo))
            registros[caso["id"]] = registro
    return registros


def regenerar_reporte(salida):
    """Genera solo el TXT desde datos guardados, incluso de versiones anteriores.

    No requiere mapas ni politica disponibles y no modifica el manifiesto.
    """
    destino = Path(salida)
    if not (destino / "manifiesto.json").is_file():
        raise ValueError("La carpeta no contiene un manifiesto de benchmark.")
    import fcntl
    with (destino / ".ejecucion.lock").open("a") as bloqueo:
        try:
            fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Hay un benchmark activo en esta carpeta; su reporte se actualiza automaticamente.") from error
        manifiesto = json.loads((destino / "manifiesto.json").read_text(encoding="utf-8"))
        config = manifiesto["identidad"]["configuracion"]
        casos = construir_casos(config)
        registros = cargar_registros(destino, casos, manifiesto["firma"], config["parametros"]["max_turnos"])
        exportar_txt(destino, config, casos, registros)
    return destino / "reporte_benchmark.txt"


def ejecutar_benchmark(configuracion, salida, limite_ejecuciones=None, simulador=simular):
 
    if limite_ejecuciones is not None and (type(limite_ejecuciones) is not int or limite_ejecuciones < 1):
        raise ValueError("El limite de ejecuciones debe ser un entero positivo.")
    config, politica_genetica = preparar_configuracion(configuracion)
    identidad = construir_identidad(config)
    firma = huella(identidad)
    casos = construir_casos(config)
    destino = Path(salida)
    destino.mkdir(parents=True, exist_ok=True)
    # flock libera el bloqueo automaticamente incluso al interrumpir el proceso.
    import fcntl
    with (destino / ".ejecucion.lock").open("a") as bloqueo:
        try:
            fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Ya hay un benchmark usando esta carpeta.") from error
        manifiesto = destino / "manifiesto.json"
        if manifiesto.exists():
            anterior = json.loads(manifiesto.read_text(encoding="utf-8"))
            if anterior.get("firma") != firma or anterior.get("identidad") != identidad:
                raise ValueError("La carpeta pertenece a otra configuracion o version; usa otra salida.")
        else:
            if (destino / "runs").exists() and any((destino / "runs").iterdir()):
                raise ValueError("Existen runs sin manifiesto; usa otra carpeta.")
            git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True)
            guardar_json(manifiesto, {"firma": firma, "identidad": identidad,
                "creado_utc": datetime.now(timezone.utc).isoformat(),
                "git_commit": git.stdout.strip() if git.returncode == 0 else None,
                "total_ejecuciones": len(casos)})

        registros = cargar_registros(destino, casos, firma, config["parametros"]["max_turnos"])

        nuevas = 0
        errores = 0
        try:
            exportar_txt(destino, config, casos, registros)
            for caso in casos:
                if caso["id"] in registros:
                    continue
                if limite_ejecuciones is not None and nuevas + errores >= limite_ejecuciones:
                    break
                escenario = dict(config["parametros"], mapa=caso["mapa"], poblacion_inicial=caso["poblacion_inicial"])
                politica = politica_genetica if caso["algoritmo"] == "genetico" else caso["algoritmo"]
                inicio = time.perf_counter()
                try:
                    resultado = simulador(politica, escenario, caso["semilla"])
                    validar_resultado(resultado, caso, escenario["max_turnos"])
                except Exception as error:
                    errores += 1
                    guardar_json(destino / "errores" / f"{caso['id']}.json", {
                        "firma": firma, "caso": caso, "tipo": type(error).__name__,
                        "mensaje": str(error), "fecha_utc": datetime.now(timezone.utc).isoformat()
                    })
                    print("ERROR", caso["algoritmo"], Path(caso["mapa"]).name,
                          caso["poblacion_inicial"], caso["semilla"], str(error), flush=True)
                    continue
                registro = {"firma": firma, "caso": caso, "resultado": resultado,
                            "segundos_ejecucion": time.perf_counter() - inicio}
                guardar_json(destino / "runs" / f"{caso['id']}.json", registro)
                registros[caso["id"]] = registro
                nuevas += 1
                exportar_csv(destino, casos, registros)
                exportar_txt(destino, config, casos, registros)
                print(f"[{len(registros)}/{len(casos)}] {caso['algoritmo']} "
                      f"{Path(caso['mapa']).name} N={caso['poblacion_inicial']} "
                      f"semilla={caso['semilla']} supervivencia={resultado['supervivencia']:.3f} "
                      f"pendientes={resultado['pendientes']}", flush=True)
        finally:
            # Ctrl+C conserva los runs completos; el que estaba en curso se repetira.
            exportar_csv(destino, casos, registros)
            exportar_txt(destino, config, casos, registros)
            progreso = {"total": len(casos), "completadas": len(registros),
                        "por_ejecutar": len(casos) - len(registros),
                        "errores_esta_invocacion": errores}
            guardar_json(destino / "progreso.json", progreso)
        return progreso


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Archivo JSON de configuracion")
    parser.add_argument("--salida", required=True, help="Carpeta de resultados y puntos de guardado")
    parser.add_argument("--solo-reporte", action="store_true", help="Generar el TXT de datos guardados sin ejecutar simulaciones")
    parser.add_argument("--limite-ejecuciones", type=int, help="Detenerse tras esta cantidad de intentos nuevos")
    args = parser.parse_args()
    try:
        if args.solo_reporte:
            if args.config or args.limite_ejecuciones is not None:
                raise ValueError("--solo-reporte solo necesita --salida.")
            print("Reporte guardado: " + str(regenerar_reporte(args.salida)))
            return 0
        if not args.config:
            raise ValueError("Indica --config para ejecutar o --solo-reporte para exportar datos guardados.")
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        progreso = ejecutar_benchmark(config, args.salida, args.limite_ejecuciones)
        print(json.dumps(progreso, ensure_ascii=False))
        return 1 if progreso["errores_esta_invocacion"] else 0
    except KeyboardInterrupt:
        print("Interrumpido: vuelve a ejecutar el mismo comando para continuar.")
        return 130
    except (ValueError, OSError, TypeError, KeyError) as error:
        print("No se pudo iniciar el benchmark: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
