"""Única traducción de estado interno a los dos formatos JSON acordados con Unity."""

from copy import deepcopy

import numpy as np

from .config import ABIERTO, COLUMNAS, ENTRADA, FILAS


def serializar_bordes(matriz):
    # 4 significa pared dañada en Unity. Una entrada siempre viaja como hueco 0.
    return np.where(matriz == ENTRADA, ABIERTO, matriz).ravel(order="C").tolist()


def estado_unity(model):
    agentes = []
    for a in model.agentes:
        agentes.append({"id": a.id, "nombre": f"S{a.id}", "x": int(a.posicion[1]), "y": int(a.posicion[0]),
                        "actionPoints": a.ap, "apGuardados": a.ap_guardados,
                        "cargandoVictima": a.victima_id is not None, "entrada": a.entrada,
                        "tareaId": a.tarea_id or 0})
    entradas = []
    for nombre, entrada in model.mapa.entradas.items():
        orientacion, r, c = entrada["borde"]
        entradas.append({"nombre": nombre, "row": r, "col": c, "esVertical": orientacion == "vertical",
                         "interior": {"x": entrada["interior"][1], "y": entrada["interior"][0]},
                         "exterior": {"x": entrada["exterior"][1], "y": entrada["exterior"][0]}})
    return {
        "turno": model.turno, "filas": FILAS, "columnas": COLUMNAS,
        "tablero": model.fuego.ravel(order="C").tolist(),
        "pois": model.pois.ravel(order="C").tolist(),
        "poisRevelado": model.pois_revelado.ravel(order="C").tolist(),
        "paredesVerticales": serializar_bordes(model.mapa.verticales),
        "paredesHorizontales": serializar_bordes(model.mapa.horizontales),
        "agentes": agentes, "victimasRescatadas": model.victimas_rescatadas,
        "victimasPerdidas": model.victimas_perdidas, "danoEstructura": model.mapa.dano_estructura,
        "entradas": entradas, "terminado": model.is_terminado(), "resultado": model.resultado,
        "siguienteAgenteId": 0 if model.is_terminado() else model.agentes[model.turno % len(model.agentes)].id,
        "semilla": model.semilla, "versionProtocolo": 1,
    }


def turno_unity(model, agente_id=0):
    return {"turno": model.turno, "agenteId": agente_id,
            "eventos": deepcopy(model.eventos), "estadoFinal": estado_unity(model)}

