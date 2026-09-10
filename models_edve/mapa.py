"""Geometría del mapa dibujado por el usuario y daño persistente de sus paredes."""

from copy import deepcopy

import numpy as np

from .config import (ABIERTO, COLUMNAS, COSTOS, DIRECCIONES, ENTRADA, ENTRADAS,
                     FILAS, PARED, PARED_DANADA, PUERTA_ABIERTA, PUERTA_CERRADA)


class Mapa:
    def __init__(self):
        self.entradas = deepcopy(ENTRADAS)
        self.verticales = np.zeros((FILAS, COLUMNAS + 1), dtype=int)
        self.horizontales = np.zeros((FILAS + 1, COLUMNAS), dtype=int)
        self.danos_verticales = np.zeros_like(self.verticales)
        self.danos_horizontales = np.zeros_like(self.horizontales)
        self.verticales[:, (0, COLUMNAS)] = PARED
        self.horizontales[(0, FILAS), :] = PARED
        self.verticales[:, (2, 5)] = PARED
        self.horizontales[(2, 4), :] = PARED
        for pos in ((1, 2), (4, 2), (2, 5), (5, 5), (0, 2), (3, 5), (5, 2)):
            self.verticales[pos] = ABIERTO
        for pos in ((2, 1), (2, 6), (4, 3), (4, 7), (2, 0)):
            self.horizontales[pos] = ABIERTO
        for pos in ((0, 3), (1, 3), (2, 6), (4, 7)):
            self.verticales[pos] = PARED
        for pos in ((2, 4), (2, 6), (4, 7)):
            self.horizontales[pos] = PARED
        for pos in ((1, 5), (2, 2), (3, 6), (5, 5), (5, 7)):
            self.verticales[pos] = PUERTA_CERRADA
        for pos in ((2, 7), (4, 3)):
            self.horizontales[pos] = PUERTA_CERRADA
        for entrada in self.entradas.values():
            orientacion, r, c = entrada["borde"]
            self.matriz(orientacion == "vertical")[r, c] = ENTRADA

    @staticmethod
    def es_interior(posicion):
        r, c = posicion
        return 0 <= r < FILAS and 0 <= c < COLUMNAS

    def matriz(self, es_vertical):
        return self.verticales if es_vertical else self.horizontales

    def borde_entre(self, origen, destino):
        """También identifica el borde exterior que detiene una explosión."""
        r, c = origen
        nr, nc = destino
        if abs(nr - r) + abs(nc - c) != 1:
            raise ValueError("Las posiciones deben ser vecinas ortogonales.")
        vertical = r == nr
        indice = (r, max(c, nc)) if vertical else (max(r, nr), c)
        matriz = self.matriz(vertical)
        if not (0 <= indice[0] < matriz.shape[0] and 0 <= indice[1] < matriz.shape[1]):
            raise ValueError("El borde está fuera del mapa.")
        return vertical, indice

    def estado_entre(self, origen, destino):
        vertical, indice = self.borde_entre(origen, destino)
        return int(self.matriz(vertical)[indice])

    def es_cruce_entrada(self, origen, destino):
        return any((origen, destino) in ((e["interior"], e["exterior"]),
                                        (e["exterior"], e["interior"]))
                   for e in self.entradas.values())

    def puede_pasar(self, origen, destino, exterior=False):
        if abs(origen[0] - destino[0]) + abs(origen[1] - destino[1]) != 1:
            return False
        interiores = self.es_interior(origen) and self.es_interior(destino)
        if not interiores and not (exterior and self.es_cruce_entrada(origen, destino)):
            return False
        return self.estado_entre(origen, destino) in (ABIERTO, PUERTA_ABIERTA, ENTRADA)

    def vecinos(self, posicion):
        if self.es_interior(posicion):
            for dr, dc in DIRECCIONES:
                vecino = (posicion[0] + dr, posicion[1] + dc)
                if self.es_interior(vecino):
                    yield vecino
        for entrada in self.entradas.values():
            interior, exterior = entrada["interior"], entrada["exterior"]
            if posicion in (interior, exterior) and self.puede_pasar(interior, exterior, exterior=True):
                yield exterior if posicion == interior else interior

    def costo_preparacion(self, origen, destino):
        return {PARED: 2 * COSTOS["golpear"], PARED_DANADA: COSTOS["golpear"],
                PUERTA_CERRADA: COSTOS["abrir"]}.get(self.estado_entre(origen, destino), 0)

    @property
    def dano_estructura(self):
        # Las dos marcas permanecen contabilizadas después de destruir el segmento.
        return int(self.danos_verticales.sum() + self.danos_horizontales.sum())

    def danar_pared(self, origen, destino):
        vertical, indice = self.borde_entre(origen, destino)
        matriz = self.matriz(vertical)
        if matriz[indice] not in (PARED, PARED_DANADA):
            return None
        danos = self.danos_verticales if vertical else self.danos_horizontales
        danos[indice] += 1
        matriz[indice] = PARED_DANADA if danos[indice] == 1 else ABIERTO
        return {"esPared": True, "row": int(indice[0]), "col": int(indice[1]),
                "esVertical": vertical, "estadoNuevo": int(matriz[indice]),
                "danoEstructura": self.dano_estructura}
