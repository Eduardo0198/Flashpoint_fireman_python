"""Bolsa finita de 12 víctimas y 6 falsas alarmas, compartida por toda la partida."""

import numpy as np

from .config import COLUMNAS, FILAS, N_POIS_OBJETIVO, VACIO


def sacar_poi_de_bolsa(model):
    bolsa = model.bolsa_pois
    disponibles = ["victima"] * bolsa["victima"] + ["falsa_alarma"] * bolsa["falsa_alarma"]
    if not disponibles:
        return None
    tipo = model.random.choice(disponibles)
    bolsa[tipo] -= 1
    return 2 if tipo == "victima" else 1


def perder_poi(model, posicion):
    valor = int(model.pois[posicion])
    if not valor:
        return
    model.pois_revelado[posicion] = True
    model.pois[posicion] = 0
    if valor == 2:
        model.victimas_perdidas += 1
    model.emitir("victima_perdida" if valor == 2 else "falsa_alarma_quemada",
                 row=posicion[0], col=posicion[1], tipoPoi=valor, enBrazos=False,
                 victimasPerdidas=model.victimas_perdidas)


def reponer_pois(model):
    while np.count_nonzero(model.pois) < N_POIS_OBJETIVO and sum(model.bolsa_pois.values()):
        r = model.random.randint(0, FILAS - 1)
        c = model.random.randint(0, COLUMNAS - 1)
        model.emitir("tirar_dados", dado1=r + 1, dado2=c + 1, proposito="poi")
        if model.pois[r, c]:
            continue
        valor = sacar_poi_de_bolsa(model)
        anterior = int(model.fuego[r, c])
        model.fuego[r, c] = VACIO
        model.pois[r, c] = valor
        model.pois_revelado[r, c] = False
        model.emitir("poi_cae", row=r, col=c, tipoPoi=valor, revelado=False,
                     apagaFuego=anterior != VACIO, estadoAnterior=anterior)

