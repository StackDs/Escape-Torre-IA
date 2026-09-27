"""Catálogo y estado compartidos. Los JSON oficiales son la fuente de parámetros."""
import json
import math
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from PyQt5 import QtCore
from src.algorithms.Genetic.politica import obtener_politica_genetica

RAIZ = Path(__file__).resolve().parents[2]
AMBIENTES = ('principal',)
ALGORITMOS = ('bfs', 'dfs', 'ucs', 'a_star', 'greedy', 'ida_star', 'genetico')


def cargar_perfil(ambiente='principal'):
    if ambiente not in AMBIENTES:
        raise ValueError('Ambiente desconocido.')
    return json.loads((RAIZ / 'configs/experimentos' / (ambiente + '.json')).read_text())


def semillas_reservadas():
    # Mantener también la reserva histórica evita reutilizar datos de evaluación.
    return set(range(20000, 20020)) | set(range(30000, 30200)) | {s for a in AMBIENTES for s in cargar_perfil(a)['semillas']}


def leer_configuracion(ruta):
    datos = json.loads(Path(ruta).read_text(encoding='utf-8'))
    if 'identidad' in datos:
        datos = datos['identidad']['configuracion']
    return deepcopy(datos)


def validar_politica(ruta, semillas=()):
    politica, _, datos = obtener_politica_genetica(ruta, permitir_por_defecto=False)
    usadas = datos.get('semillas_entrenamiento')
    if not isinstance(usadas, list) or not usadas or any(type(s) is not int for s in usadas):
        raise ValueError('La política debe registrar semillas de entrenamiento válidas.')
    aptitud = datos.get('aptitud_entrenamiento')
    if not isinstance(aptitud, (int, float)) or not math.isfinite(aptitud) or not 0 <= aptitud <= 1:
        raise ValueError('La política no contiene una aptitud de entrenamiento válida.')
    if set(usadas) & set(semillas):
        raise ValueError('Las semillas de entrenamiento coinciden con las de evaluación.')
    return politica, datos


def guardar_copia(ruta, config):
    ruta = Path(ruta).resolve()
    if ruta.is_relative_to((RAIZ / 'configs').resolve()):
        raise ValueError('Los archivos del catálogo son de solo lectura. Guarda la copia fuera de configs.')
    if ruta.exists():
        raise ValueError('El destino ya existe. Elige un nombre nuevo para conservar su contenido.')
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open('x', encoding='utf-8') as archivo:
        json.dump(config, archivo, ensure_ascii=False, indent=2)
        archivo.write('\n')


def nuevo_destino(base, nombre):
    return Path(base) / (nombre + '_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid4().hex[:6])


class EstadoGUI(QtCore.QObject):
    ambiente_cambiado = QtCore.pyqtSignal(str)
    politica_cambiada = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ambiente = 'principal'
        self.politica = ''
        ruta = cargar_perfil().get('politica_genetica')
        if ruta:
            try:
                self.elegir_politica(RAIZ / ruta)
            except (ValueError, OSError, TypeError, KeyError):
                pass  # El formulario exigirá elegir una política válida antes de ejecutar.
        self.ocupado = None

    def elegir_ambiente(self, ambiente):
        if ambiente in AMBIENTES and ambiente != self.ambiente:
            self.ambiente = ambiente
            self.ambiente_cambiado.emit(ambiente)

    def elegir_politica(self, ruta):
        validar_politica(ruta)
        self.politica = str(Path(ruta).resolve())
        self.politica_cambiada.emit(self.politica)

    def adquirir(self, propietario):
        if self.ocupado is not None and self.ocupado is not propietario:
            raise ValueError('Ya hay un cálculo activo. Detén o espera la ejecución actual.')
        self.ocupado = propietario

    def liberar(self, propietario):
        if self.ocupado is propietario:
            self.ocupado = None


def estado_compartido(parent):
    return getattr(parent, 'estado_gui', None) or EstadoGUI()
