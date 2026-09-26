
import math
import random
from copy import deepcopy

from ..models.agente import Agente, State
from ..models.mapa import cargar_mapa
from .fuego import seleccionar_focos, encender_focos, propagar_fuego
from .movimiento import resolver_movimientos, aplicar_movimientos
from .politicas import PoliticaBusqueda, ruta_valida


VALORES_INICIALES = {
    "capacidad_pasillos": 4,
    "capacidad_salida": 2,
    "cantidad_focos": 2,
    "k": 3,
    "probabilidad": 0.4,
    "max_turnos": 1000,
    "alpha": 1.0,
    "umbral_bloqueo": 3
}


def validar_posiciones(posiciones, mapa, nombre):
    
    if not isinstance(posiciones, (list, tuple)):
        return None
    filas, columnas = mapa.shape
    resultado = []
    for posicion in posiciones:
        if not isinstance(posicion, (list, tuple)) or len(posicion) != 2:
             return None
        fila, columna = posicion
        if type(fila) is not int or type(columna) is not int:
             return None
        if not (0 <= fila < filas and 0 <= columna < columnas):
             return None
        resultado.append((fila, columna))
    return resultado


class MotorSimulacion:
    def __init__(self, politica, escenario, semilla):
        if not isinstance(escenario, dict):
            raise ValueError("El escenario debe ser un diccionario.")
        if "mapa" not in escenario or "poblacion_inicial" not in escenario:
            raise ValueError("El escenario requiere mapa y poblacion_inicial.")
        if type(semilla) is not int:
            raise ValueError("La semilla debe ser un entero.")
        permitidos = set(VALORES_INICIALES) | {
            "mapa", "poblacion_inicial", "focos", "posiciones_iniciales"
        }
        if set(escenario) - permitidos:
            raise ValueError("El escenario contiene parametros desconocidos.")
        self.escenario = deepcopy(VALORES_INICIALES)
        self.escenario.update(deepcopy(escenario))
        self.semilla = semilla
        self.turno = 0
        self.terminada = False
        self.motivo_termino = None
        self.agentes = []
        if self._validar_configuracion() is None:
            raise ValueError("Parametros invalidos: revisa poblacion, capacidades, fuego y limites.")

        if isinstance(politica, str):
            politica = PoliticaBusqueda(
                politica, self.escenario["alpha"], self.escenario["umbral_bloqueo"]
            )
        if not callable(getattr(politica, "planificar", None)):
            raise ValueError("La politica debe tener un metodo planificar.")
        if not callable(getattr(politica, "necesita_replanificar", None)):
            raise ValueError("La politica debe tener un metodo necesita_replanificar.")
        # Evitar compartir estado de una politica entre ejecuciones.
        self.politica = deepcopy(politica)
        self.mapa = cargar_mapa(self.escenario["mapa"])
        for celda in self.mapa.flat:
            if celda.simbolo == ".":
                celda.capacidad = self.escenario["capacidad_pasillos"]
            elif celda.simbolo == "E":
                celda.capacidad = self.escenario["capacidad_salida"]

        # Derivar siempre las cuatro semillas, incluso con posiciones manuales.
        origen = random.Random(semilla)
        self.semillas = {}
        for nombre in ("focos", "posiciones", "fuego", "conflictos"):
            self.semillas[nombre] = origen.getrandbits(64)
        self.azar_fuego = random.Random(self.semillas["fuego"])
        self.azar_conflictos = random.Random(self.semillas["conflictos"])

        # Las posiciones manuales se reservan antes de elegir focos aleatorios.
        manuales = self.escenario.get("posiciones_iniciales")
        if "posiciones_iniciales" in self.escenario:
            manuales = validar_posiciones(manuales, self.mapa, "posiciones_iniciales")
            if manuales is None:
                raise ValueError("Las posiciones iniciales son invalidas.")
            if len(manuales) != self.escenario["poblacion_inicial"]:
                raise ValueError("La cantidad de posiciones no coincide con la poblacion.")
            if self._crear_agentes(manuales) is None:
                raise ValueError("Las posiciones iniciales no respetan terreno o capacidad.")

        if "focos" in self.escenario:
            focos = validar_posiciones(self.escenario["focos"], self.mapa, "focos")
            if focos is None:
                raise ValueError("Las posiciones de los focos son invalidas.")
            if "cantidad_focos" in escenario and len(focos) != escenario["cantidad_focos"]:
                raise ValueError("cantidad_focos no coincide con los focos explicitos.")
        else:
            focos = seleccionar_focos(
                self.mapa, self.escenario["cantidad_focos"], self.semillas["focos"]
            )
        if focos is None:
            raise ValueError("No hay suficientes celdas disponibles para los focos.")
        self.focos = encender_focos(self.mapa, focos)
        if self.focos is None:
            raise ValueError("Focos invalidos: revisa muros, salida, duplicados y agentes.")
        self.escenario["cantidad_focos"] = len(self.focos)

        if manuales is None:
            # Cada entrada representa un espacio fisico disponible.
            espacios = []
            filas, columnas = self.mapa.shape
            for fila in range(filas):
                for columna in range(columnas):
                    celda = self.mapa[fila, columna]
                    if celda.simbolo == "." and not celda.quemada:
                        espacios.extend([(fila, columna)] * celda.capacidad)
            cantidad = self.escenario["poblacion_inicial"]
            if cantidad > len(espacios):
                raise ValueError("No hay capacidad suficiente para la poblacion inicial.")
            azar_posiciones = random.Random(self.semillas["posiciones"])
            if self._crear_agentes(azar_posiciones.sample(espacios, cantidad)) is None:
                raise ValueError("No se pudo inicializar la poblacion solicitada.")
        self.posiciones_iniciales = [agente.obtener_posicion() for agente in self.agentes]

    def _validar_configuracion(self):
        for nombre in ("poblacion_inicial", "capacidad_pasillos", "capacidad_salida",
                       "k", "max_turnos", "umbral_bloqueo"):
            valor = self.escenario[nombre]
            if type(valor) is not int or valor < 1:
                return None
        cantidad = self.escenario["cantidad_focos"]
        if type(cantidad) is not int or cantidad < 0:
             return None
        for nombre in ("probabilidad", "alpha"):
            valor = self.escenario[nombre]
            if not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
                 return None
        if self.escenario["probabilidad"] > 1:
             return None
        return True

    def _crear_agentes(self, posiciones):
        for identificador, posicion in enumerate(posiciones):
            celda = self.mapa[posicion]
            if celda.simbolo != "." or celda.quemada:
                 return None
            if len(celda.agentes) >= celda.capacidad:
                 return None
            agente = Agente(identificador, posicion[0], posicion[1])
            self.agentes.append(agente)
            celda.agentes.append(agente)
        return True

    def avanzar_turno(self):
        if self.terminada:
            return self.resultado()
        self.turno += 1
        nuevas = propagar_fuego(
            self.mapa, self.turno, self.escenario["k"],
            self.escenario["probabilidad"], self.azar_fuego
        )
        if nuevas is None:
            raise ValueError("El modulo de fuego rechazo los parametros de propagacion.")

        vivos = []
        for agente in self.agentes:
            if agente.estado not in (State.ACTIVO, State.ESPERANDO):
                continue
            celda = self.mapa[agente.obtener_posicion()]
            if celda.quemada:
                agente.estado = State.MUERTO
                agente.turno_fallecimiento = self.turno
                agente.borrar_ruta()
                celda.agentes.remove(agente)
            else:
                vivos.append(agente)

        # Todas las busquedas observan la misma ocupacion y el mismo fuego
        rutas_del_turno = {}
        busqueda_normal = type(self.politica) is PoliticaBusqueda
        for agente in vivos:
            posicion = agente.obtener_posicion()
            invalida = not ruta_valida(self.mapa, posicion, agente.ruta)
            replanificar = invalida
            if not replanificar:
                if busqueda_normal:
                    replanificar = self.politica.necesita_replanificar(
                        self.mapa, agente, ruta_comprobada=True
                    )
                else:
                    replanificar = self.politica.necesita_replanificar(self.mapa, agente)
            if replanificar:
                # Dos personas en la misma celda consultan exactamente el mismo
                # problema. Compartir solo durante esta fase, incluso sin ruta.
                # Las politicas externas pueden depender de su propio estado.
                if busqueda_normal and posicion in rutas_del_turno:
                    ruta = rutas_del_turno[posicion]
                else:
                    ruta = self.politica.planificar(self.mapa, posicion)
                    if busqueda_normal:
                        rutas_del_turno[posicion] = ruta
                agente.turnos_bloqueado = 0
                if ruta is None:
                    # asignar_ruta tambien cuenta intentos sin solucion
                    agente.asignar_ruta([])
                else:
                    if not ruta_valida(self.mapa, posicion, ruta):
                        raise ValueError("La politica devolvio una ruta invalida.")
                    agente.asignar_ruta([tuple(paso) for paso in ruta])

        aceptados = resolver_movimientos(self.mapa, vivos, self.azar_conflictos)
        aplicar_movimientos(self.mapa, vivos, aceptados, self.turno)
        pendientes = any(
            agente.estado in (State.ACTIVO, State.ESPERANDO)
            for agente in self.agentes
        )
        if not pendientes:
            self.terminada = True
            self.motivo_termino = "sin_agentes_pendientes"
        elif self.turno >= self.escenario["max_turnos"]:
            self.terminada = True
            self.motivo_termino = "max_turnos"
        return self.resultado()

    def ejecutar(self):
        while not self.terminada:
            self.avanzar_turno()
        return self.resultado()

    def resultado(self):
        evacuados = sum(agente.estado == State.EVACUADO for agente in self.agentes)
        fallecidos = sum(agente.estado == State.MUERTO for agente in self.agentes)
        turnos_evacuacion = [
            agente.turno_evacuacion for agente in self.agentes
            if agente.estado == State.EVACUADO
        ]
        return {
            "evacuados": evacuados,
            "fallecidos": fallecidos,
            "pendientes": len(self.agentes) - evacuados - fallecidos,
            "supervivencia": evacuados / len(self.agentes),
            "turnos_ejecutados": self.turno,
            "turno_ultimo_evacuado": max(turnos_evacuacion, default=None),
            "motivo_termino": self.motivo_termino,
            "movimientos": sum(agente.movimientos for agente in self.agentes),
            "esperas": sum(agente.esperas for agente in self.agentes),
            "planificaciones": sum(agente.replanificaciones for agente in self.agentes)
        }


def simular(politica, escenario, semilla):
    return MotorSimulacion(politica, escenario, semilla).ejecutar()
