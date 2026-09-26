class Celda:
    def __init__(self, simbolo, capacidad):
        self.simbolo = simbolo
        self.capacidad = capacidad
        self.agentes = []
        self.quemada = False

    def quemar(self):
        self.quemada = True

