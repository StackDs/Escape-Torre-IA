import math


class Individuo:
    """Una estrategia compartida por los agentes, no una persona del mapa."""

    def __init__(self, peso_congestion, peso_riesgo, umbral_bloqueo):
        if not math.isfinite(peso_congestion) or peso_congestion < 0:
            raise ValueError("El peso de congestion debe ser finito y no negativo.")
        if not math.isfinite(peso_riesgo) or peso_riesgo < 0:
            raise ValueError("El peso de riesgo debe ser finito y no negativo.")
        if type(umbral_bloqueo) is not int or umbral_bloqueo < 1:
            raise ValueError("El umbral de bloqueo debe ser un entero positivo.")

        self.peso_congestion = float(peso_congestion)
        self.peso_riesgo = float(peso_riesgo)
        self.umbral_bloqueo = umbral_bloqueo
        self.aptitud = None

    def copiar(self):
        copia = Individuo(
            self.peso_congestion,
            self.peso_riesgo,
            self.umbral_bloqueo
        )
        copia.aptitud = self.aptitud
        return copia

    def parametros(self):
        return {
            "peso_congestion": self.peso_congestion,
            "peso_riesgo": self.peso_riesgo,
            "umbral_bloqueo": self.umbral_bloqueo
        }
