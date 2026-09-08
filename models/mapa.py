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
DANO_MAXIMO = 2

# Puertas configurables: coordenadas reales del tablero.
PUERTAS_VERTICALES = [(0, 2)]
PUERTAS_HORIZONTALES = [(2, 4)]


def crear_tablero():
    return np.zeros((FILAS_JUGABLES, COLUMNAS_JUGABLES), dtype=int)


def poner_pared_vertical(paredes_verticales, fila, limite_columna):
    paredes_verticales[fila, limite_columna] = PARED


def poner_pared_horizontal(paredes_horizontales, limite_fila, columna):
    paredes_horizontales[limite_fila, columna] = PARED


def poner_puerta_vertical(paredes_verticales, fila, limite_columna, abierta=False):
    paredes_verticales[fila, limite_columna] = PUERTA_ABIERTA if abierta else PUERTA_CERRADA


def poner_puerta_horizontal(paredes_horizontales, limite_fila, columna, abierta=False):
    paredes_horizontales[limite_fila, columna] = PUERTA_ABIERTA if abierta else PUERTA_CERRADA


def crear_paredes():
    paredes_verticales = np.zeros((FILAS_JUGABLES, COLUMNAS_JUGABLES + 1), dtype=int)
    paredes_horizontales = np.zeros((FILAS_JUGABLES + 1, COLUMNAS_JUGABLES), dtype=int)

    # Marco exterior.
    paredes_verticales[:, 0] = PARED
    paredes_verticales[:, -1] = PARED
    paredes_horizontales[0, :] = PARED
    paredes_horizontales[-1, :] = PARED

    # Divisiones internas (plantilla de habitaciones).
    for fila in range(FILAS_JUGABLES):
        poner_pared_vertical(paredes_verticales, fila, 2)
        poner_pared_vertical(paredes_verticales, fila, 5)

    for columna in range(COLUMNAS_JUGABLES):
        poner_pared_horizontal(paredes_horizontales, 2, columna)
        poner_pared_horizontal(paredes_horizontales, 4, columna)

    # Aberturas que no son puertas (huecos libres en las divisiones).
    paredes_verticales[1, 2] = ABIERTO
    paredes_verticales[4, 2] = ABIERTO
    paredes_verticales[2, 5] = ABIERTO
    paredes_verticales[5, 5] = ABIERTO
    paredes_horizontales[2, 1] = ABIERTO
    paredes_horizontales[2, 6] = ABIERTO
    paredes_horizontales[4, 3] = ABIERTO
    paredes_horizontales[4, 7] = ABIERTO

    # Puertas (empiezan cerradas).
    for fila, limite_columna in PUERTAS_VERTICALES:
        poner_puerta_vertical(paredes_verticales, fila, limite_columna)

    for limite_fila, columna in PUERTAS_HORIZONTALES:
        poner_puerta_horizontal(paredes_horizontales, limite_fila, columna)

    return paredes_verticales, paredes_horizontales

def crear_danos():
    danos_verticales = np.zeros((FILAS_JUGABLES, COLUMNAS_JUGABLES + 1), dtype = int)
    danos_horizontales = np.zeros((FILAS_JUGABLES + 1, COLUMNAS_JUGABLES), dtype = int)
    return danos_verticales, danos_horizontales

def abrir_puerta_vertical(paredes_verticales, fila, limite_columna):
    if paredes_verticales[fila, limite_columna] == PUERTA_CERRADA:
        paredes_verticales[fila, limite_columna] = PUERTA_ABIERTA


def abrir_puerta_horizontal(paredes_horizontales, limite_fila, columna):
    if paredes_horizontales[limite_fila, columna] == PUERTA_CERRADA:
        paredes_horizontales[limite_fila, columna] = PUERTA_ABIERTA


def hay_bloqueo(paredes_verticales, paredes_horizontales, dano_verticales, danos_horizontales, r1, c1, r2, c2):
    if r1 == r2 and abs(c1 - c2) == 1:
        limite_columna = max(c1, c2)
        valor = paredes_verticales[r1, limite_columna]
        dano = dano_verticales[r1,limite_columna ]
    elif c1 == c2 and abs(r1 - r2) == 1:
        limite_fila = max(r1, r2)
        valor = paredes_horizontales[limite_fila, c1]
        dano =  danos_horizontales[limite_fila, c1]
    else:
        return True

    if valor == PARED:
        return dano < DANO_MAXIMO
    return valor == PUERTA_CERRADA