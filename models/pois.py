import numpy as np
import random

ROWS_POIS = 6
COLS_POIS = 8

POS_INICIALES = [(2,4), (5,1), (5,8)]

POI_POSICIONES = [
    (0,0), (0,1), (0,2), (0,3), (0,4), (0,5), (0,6), (0,7),
    (1,0), (1,1), (1,2), (1,3), (1,4), (1,5), (1,6), (1,7),
    (2,0), (2,1), (2,2), (2,3), (2,4), (2,5), (2,6), (2,7),
    (3,0), (3,1), (3,2), (3,3), (3,4), (3,5), (3,6), (3,7),
    (4,0), (4,1), (4,2), (4,3), (4,4), (4,5), (4,6), (4,7),
    (5,0), (5,1), (5,2), (5,3), (5,4), (5,5), (5,6), (5,7),
]

POIS_INICIALES = [(2, 4), (5, 1), (5, 8)]

SIN_POI = 0
POI_SIN_REVELAR = 3
VICTIMA_REVELADA= 2

#Porcentaje de victimas y falsas alarmas
PROB_VICTIMA = 12/18

def crear_matriz_pois():
    matrix = np.zeros((ROWS_POIS, COLS_POIS), dtype=int)
    for fila, columna in POIS_INICIALES:
        matrix[fila - 1, columna - 1] = 2
        matrix[fila - 1, columna - 1] = POI_SIN_REVELAR
    return matrix