"""Escaneo de cambios y tareas con reserva exclusiva entre turnos."""

from copy import deepcopy

import numpy as np

from .config import (ABIERTO, ENTRADA, FUEGO, HUMO, PARED, PARED_DANADA,
                     PRIORIDADES, PUERTA_ABIERTA, PUERTA_CERRADA, VACIO)


class Cortana:
    def __init__(self, model):
        self.model = model
        self.tareas = []
        self.historial_tareas = []
        self.historial_cambios = []
        self.ultimo_escaneo = {}
        self.siguiente_id = 1

    def buscar_tarea(self, tarea_id):
        return next((t for t in self.tareas if t["id"] == tarea_id), None)

    def cerrar_tarea(self, tarea, estado, motivo):
        tarea.update(estado=estado, motivo=motivo, turno_fin=self.model.turno)
        self.historial_tareas.append(deepcopy(tarea))
        self.tareas.remove(tarea)
        for agente in self.model.agentes:
            if agente.tarea_id == tarea["id"]:
                agente.tarea_id = None

    def gameMasterCortana(self):
        m = self.model
        actual = {}
        for r, c in np.ndindex(m.fuego.shape):
            actual[("riesgo", (r, c))] = {VACIO: None, HUMO: "humo", FUEGO: "fuego"}[int(m.fuego[r, c])]
            valor = m.pois[r, c]
            tipo = None
            if valor:
                tipo = "poi" if not m.pois_revelado[r, c] else ("victima" if valor == 2 else "falsa_alarma")
            actual[("poi", (r, c))] = tipo
        nombres = {ABIERTO: "abierto", PARED: "pared", PARED_DANADA: "pared_danada",
                   PUERTA_CERRADA: "puerta_cerrada", PUERTA_ABIERTA: "puerta_abierta", ENTRADA: "entrada"}
        for capa, matriz in (("vertical", m.mapa.verticales), ("horizontal", m.mapa.horizontales)):
            for posicion in np.ndindex(matriz.shape):
                actual[(capa, posicion)] = nombres[int(matriz[posicion])]
        cambios = []
        for (capa, posicion), valor in actual.items():
            anterior = self.ultimo_escaneo.get((capa, posicion))
            if valor != anterior:
                cambios.append({"turno": m.turno, "capa": capa, "posicion": posicion,
                                "antes": anterior, "despues": valor})
        self.ultimo_escaneo = actual
        self.historial_cambios.extend(cambios)
        for tarea in list(self.tareas):
            if tarea["fase"] == "traslado":
                portador = next(a for a in m.agentes if a.id == tarea["agente"])
                tarea["posicion"] = portador.posicion
                continue
            tipo = actual[(tarea["capa"], tarea["posicion"])]
            if tipo not in PRIORIDADES:
                self.cerrar_tarea(tarea, "cancelada", "El objetivo desapareció del mapa")
            elif tarea["tipo"] != tipo:
                tarea.update(tipo=tipo, prioridad=PRIORIDADES[tipo])
        presentes = {(t["capa"], t["posicion"]) for t in self.tareas if t["fase"] != "traslado"}
        for (capa, posicion), tipo in actual.items():
            if tipo not in PRIORIDADES or (capa, posicion) in presentes:
                continue
            self.tareas.append({"id": self.siguiente_id, "tipo": tipo, "posicion": posicion,
                                "capa": capa, "prioridad": PRIORIDADES[tipo], "estado": "disponible",
                                "agente": None, "fase": "objetivo", "turno_creada": m.turno})
            self.siguiente_id += 1
        return cambios


def gameMasterCortana(model):
    """Punto de entrada con el nombre acordado en el notebook."""
    return model.cortana.gameMasterCortana()
