"""Proceso Qt no bloqueante, con líneas completas e interrupción progresiva."""
import codecs
import os
import signal
import sys
from PyQt5 import QtCore
from .experimentos import RAIZ


class Proceso(QtCore.QObject):
    linea = QtCore.pyqtSignal(str)
    terminado = QtCore.pyqtSignal(int, bool)

    def __init__(self, estado, parent=None):
        super().__init__(parent)
        self.estado = estado
        self.proceso = None
        self.activo = False
        self.cancelado = False
        self._buffer = ''
        self._decoder = None

    def iniciar(self, argumentos):
        if self.activo:
            raise ValueError('El proceso anterior sigue activo.')
        self.estado.adquirir(self)
        self.activo = True
        self.cancelado = False
        self._buffer = ''
        self._decoder = codecs.getincrementaldecoder('utf-8')('replace')
        proceso = QtCore.QProcess(self)
        self.proceso = proceso
        proceso.setWorkingDirectory(str(RAIZ))
        proceso.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        proceso.readyReadStandardOutput.connect(self._leer)
        proceso.finished.connect(lambda codigo, estado: self._finalizar(codigo))
        proceso.errorOccurred.connect(self._error)
        proceso.started.connect(lambda: self._interrumpir(proceso) if self.cancelado else None)
        proceso.start(sys.executable, ['-u'] + list(argumentos))

    def recibir(self, datos):
        self._buffer += self._decoder.decode(datos)
        while '\n' in self._buffer:
            linea, self._buffer = self._buffer.split('\n', 1)
            self.linea.emit(linea.rstrip('\r'))

    def _leer(self):
        self.recibir(bytes(self.proceso.readAllStandardOutput()))

    def _error(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self.linea.emit('No se pudo iniciar Python: ' + self.proceso.errorString())
            self._finalizar(-1)

    def _finalizar(self, codigo):
        if not self.activo:
            return
        self._leer()
        self._buffer += self._decoder.decode(b'', final=True)
        if self._buffer:
            self.linea.emit(self._buffer)
        self._buffer = ''
        self.activo = False
        self.estado.liberar(self)
        self.terminado.emit(codigo, self.cancelado)

    def detener(self):
        if self.activo:
            self.cancelado = True
            self._interrumpir(self.proceso)

    def _interrumpir(self, proceso):
        if proceso.state() == QtCore.QProcess.Running:
            try:
                os.kill(int(proceso.processId()), signal.SIGINT)
            except ProcessLookupError:
                pass
            QtCore.QTimer.singleShot(3000, lambda: self._terminar_si_activo(proceso))

    def _terminar_si_activo(self, proceso):
        if self.proceso is proceso and proceso.state() != QtCore.QProcess.NotRunning:
            proceso.terminate()
            QtCore.QTimer.singleShot(2000, lambda: self._matar_si_activo(proceso))

    def _matar_si_activo(self, proceso):
        if self.proceso is proceso and proceso.state() != QtCore.QProcess.NotRunning:
            proceso.kill()
