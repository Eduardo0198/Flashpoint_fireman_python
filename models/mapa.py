import numpy as np

FILAS_JUGABLES = 6
COLUMNAS_JUGABLES = 8

MARCO = 9
VACIO = 0
HUMO = 1
FUEGO = 2
POI = 3
BOMBERO = 4

ABIERTO = 0
PARED = 1
PUERTA_CERRADA = 2
PUERTA_ABIERTA = 3

def crear_tablero():
    return np.zeros((FILAS_JUGABLES, COLUMNAS_JUGABLES), dtype=int)

def crear_paredes():
    paredes_verticales = np.zeros((FILAS_JUGABLES, COLUMNAS_JUGABLES + 1), dtype=int)
    paredes_horizontales = np.zeros((FILAS_JUGABLES + 1, COLUMNAS_JUGABLES), dtype=int)

    paredes_verticales[:, 0] = PARED
    paredes_verticales[:, -1] = PARED
    paredes_horizontales[0, :] = PARED
    paredes_horizontales[-1, :] = PARED

    return paredes_verticales, paredes_horizontales

def poner_pared_vertical(paredes_verticales, fila, limite_columna):
    paredes_verticales[fila, limite_columna] = PARED

def poner_pared_horizontal(paredes_horizontales, limite_fila, columna):
    paredes_horizontales[limite_fila, columna] = PARED

def poner_puerta_vertical(paredes_verticales, fila, limite_columna, abierta=False):
    paredes_verticales[fila, limite_columna] = PUERTA_ABIERTA if abierta else PUERTA_CERRADA

def poner_puerta_horizontal(paredes_horizontales, limite_fila, columna, abierta=False):
    paredes_horizontales[limite_fila, columna] = PUERTA_ABIERTA if abierta else PUERTA_CERRADA