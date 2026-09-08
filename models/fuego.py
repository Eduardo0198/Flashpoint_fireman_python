import numpy as np
import random
from models.mapa import PARED, PUERTA_CERRADA, PUERTA_ABIERTA, DANO_MAXIMO


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

def _valor_borde(paredes_verticales, paredes_horizontales, r1, c1, r2, c2):
    if r1 == r2 and abs(c1 - c2) == 1:
        return paredes_verticales[r1, max(c1, c2)]
    if c1 == c2 and abs(r1 - r2) == 1:
        return paredes_horizontales[max(r1, r2), c1]
    return PARED


def _danar_pared(danos_verticales, danos_horizontales, r1, c1, r2, c2):
    if r1 == r2 and abs(c1 - c2) == 1:
        limite = max(c1, c2)
        if danos_verticales[r1, limite] < DANO_MAXIMO:
            danos_verticales[r1, limite] += 1
            return 1
    elif c1 == c2 and abs(r1 - r2) == 1:
        limite = max(r1, r2)
        if danos_horizontales[limite, c1] < DANO_MAXIMO:
            danos_horizontales[limite, c1] += 1
            return 1
    return 0


def _quitar_puerta(paredes_verticales, paredes_horizontales, r1, c1, r2, c2):
    if r1 == r2 and abs(c1 - c2) == 1:
        paredes_verticales[r1, max(c1, c2)] = PARED
    elif c1 == c2 and abs(r1 - r2) == 1:
        paredes_horizontales[max(r1, r2), c1] = PARED

def explosion(r, c, matrix, paredes_verticales, paredes_horizontales, danos_verticales, danos_horizontales):
    direcciones = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    dano_total = 0
    for dr, dc in direcciones:
        fr, fc = r, c
        while True:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < ROWS_FUEGO and 0 <= nc < COLS_FUEGO):
                break
            
            borde = _valor_borde(paredes_verticales, paredes_horizontales, fr, fc, nr, nc)
            if borde == PARED:
                dano_total += _danar_pared(danos_verticales, danos_horizontales, fr, fc, nr, nc)
                break
            
            if borde == PUERTA_CERRADA:
                _quitar_puerta(paredes_verticales, paredes_horizontales, fr, fc, nr, nc)
                break
            if matrix[nr, nc] == 2:
                fr, fc = nr, nc
            
            if matrix[nr, nc] == 1:
                matrix[nr, nc] = 2
            else:
                matrix[nr, nc] = 2
            break
    return dano_total

def flashover(matrix, paredes_verticales, paredes_horizontales):
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
                    if not (0 <= ni < ROWS_FUEGO and 0 <= nj < COLS_FUEGO):
                        continue
                    borde = _valor_borde(paredes_verticales, paredes_horizontales, i, j, ni, nj)
                    if borde in (PARED, PUERTA_CERRADA):
                        continue  # el humo no se propaga a través de paredes o puertas cerradas
                    if matrix[ni, nj] == 2:
                        matrix[i, j] = 2
                        cambio = True
                        break

def advance_fire(matrix, paredes_verticales, paredes_horizontales, danos_verticales, danos_horizontales, rng):
    fila = rng.randint(1, ROWS_FUEGO)
    columna = rng.randint(1, COLS_FUEGO)
    r, c = fila - 1, columna - 1
    dano_nuevo = 0

    if matrix[r, c] == 0:
        matrix[r, c] = 1
    elif matrix[r, c] == 1:
        matrix[r, c] = 2
    elif matrix[r, c] == 2:
        dano_nuevo = explosion(r, c, matrix, paredes_verticales, paredes_horizontales,
                                danos_verticales, danos_horizontales)

    flashover(matrix, paredes_verticales, paredes_horizontales)
    return fila, columna, dano_nuevo