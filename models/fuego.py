import numpy as np
import random

ROWS_FUEGO = 6
COLS_FUEGO = 8

FUEGO_INICIAL = [
    (1, 7), (4, 3), (5, 2), (1, 5), (2, 2),
    (2, 6), (6, 1), (1, 8), (2, 1), (6, 4),
]

def crear_matriz_fuego():
    matrix = np.zeros((ROWS_FUEGO, COLS_FUEGO), dtype=int)
    for fila, columna in FUEGO_INICIAL:
        matrix[fila - 1, columna - 1] = 2
    return matrix

def explosion(r, c, matrix):
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for dr, dc in direcciones:
        nr, nc = r + dr, c + dc
        while 0 <= nr < ROWS_FUEGO and 0 <= nc < COLS_FUEGO and matrix[nr, nc] == 2:
            nr += dr
            nc += dc
        if 0 <= nr < ROWS_FUEGO and 0 <= nc < COLS_FUEGO:
            matrix[nr, nc] = 2

def flashover(matrix):
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    cambio = True
    while cambio:
        cambio = False
        for i in range(ROWS_FUEGO):
            for j in range(COLS_FUEGO):
                if matrix[i, j] != 1:
                    continue
                for dr, dc in direcciones:
                    ni, nj = i + dr, j + dc
                    if 0 <= ni < ROWS_FUEGO and 0 <= nj < COLS_FUEGO and matrix[ni, nj] == 2:
                        matrix[i, j] = 2
                        cambio = True
                        break

def advance_fire(matrix):
    fila = random.randint(1, ROWS_FUEGO)
    columna = random.randint(1, COLS_FUEGO)
    r, c = fila - 1, columna - 1

    if matrix[r, c] == 0:
        matrix[r, c] = 1
    elif matrix[r, c] == 1:
        matrix[r, c] = 2
    elif matrix[r, c] == 2:
        explosion(r, c, matrix)

    flashover(matrix)
    return fila, columna