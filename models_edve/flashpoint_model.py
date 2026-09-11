"""Estado por partida y orden de ejecución: un agente, fuego y reposición de POIs."""

from random import Random

import numpy as np

from .agente import Bombero
from .config import (BOLSA_POIS_INICIAL, COLUMNAS, ENTRADAS_AGENTES, FILAS,
                     FUEGO, FUEGO_INICIAL, POIS_INICIALES, Reglas)
from .cortana import Cortana
from .fuego import avanzar_fuego, flashover
from .mapa import Mapa
from .pois import reponer_pois, sacar_poi_de_bolsa
from .protocolo_unity import estado_unity, turno_unity


class FlashPoint:
    def __init__(self, semilla=42, num_agentes=6, *, reglas=None, entradas_agentes=None):
        if type(semilla) is not int:
            raise ValueError("semilla debe ser un entero.")
        if type(num_agentes) is not int or not 1 <= num_agentes <= 6:
            raise ValueError("num_agentes debe estar entre 1 y 6.")
        self.semilla = semilla
        self.reglas = reglas or Reglas()
        self.random = Random(semilla)
        self.mapa = Mapa()
        entradas = tuple(entradas_agentes) if entradas_agentes is not None else ENTRADAS_AGENTES[:num_agentes]
        if len(entradas) != num_agentes or any(e not in self.mapa.entradas for e in entradas):
            raise ValueError("Debe haber una entrada válida por agente.")
        self.fuego = np.zeros((FILAS, COLUMNAS), dtype=int)
        self.pois = np.zeros((FILAS, COLUMNAS), dtype=int)
        self.pois_revelado = np.zeros((FILAS, COLUMNAS), dtype=bool)
        self.bolsa_pois = BOLSA_POIS_INICIAL.copy()
        for pos in POIS_INICIALES:
            self.pois[pos] = sacar_poi_de_bolsa(self)
        for pos in FUEGO_INICIAL:
            self.fuego[pos] = FUEGO
        self.turno = 0
        self.resultado = None
        self.victimas_rescatadas = 0
        self.victimas_perdidas = 0
        self.tiradas_fuego = 0
        self.eventos = []
        self.agentes = [Bombero(self, i + 1, entrada) for i, entrada in enumerate(entradas)]
        self.cortana = Cortana(self)
        self.gameMasterCortana()

    def emitir(self, tipo, **datos):
        self.eventos.append({"tipo": tipo, **datos})

    def gameMasterCortana(self):
        return self.cortana.gameMasterCortana()

    def hay_colapso(self):
        limite = self.reglas.dano_para_colapso
        return limite is not None and self.mapa.dano_estructura >= limite

    def evaluar_resultado(self):
        if self.victimas_rescatadas >= self.reglas.victimas_para_ganar:
            return "victoria"
        if self.victimas_perdidas >= self.reglas.victimas_para_perder:
            return "derrota_victimas"
        if self.hay_colapso():
            return "derrota_colapso"
        return None

    def is_terminado(self):
        return self.resultado is not None

    def to_dict(self):
        return estado_unity(self)

    def step(self, ahorrar=False):
        if type(ahorrar) is not bool:
            raise ValueError("ahorrar debe ser booleano.")
        self.eventos = []
        if self.is_terminado():
            return turno_unity(self)
        self.turno += 1
        agente = self.agentes[(self.turno - 1) % len(self.agentes)]
        agente.step(ahorrar=ahorrar)
        self.resultado = self.evaluar_resultado()
        # Rescate ganador o colapso por hachazo: la partida termina en esa acción.
        if self.resultado is None:
            avanzar_fuego(self)
            self.gameMasterCortana()
            if not self.hay_colapso():
                flashover(self)
            self.gameMasterCortana()
            for bombero in self.agentes:
                bombero.retirarse_por_fuego()
            self.gameMasterCortana()
            self.resultado = self.evaluar_resultado()
            if self.resultado is None:
                reponer_pois(self)
                self.gameMasterCortana()
                if self.turno >= self.reglas.max_turnos:
                    self.resultado = "sin_resolver"
        if self.is_terminado():
            self.emitir("partida_terminada", resultado=self.resultado,
                        victimasRescatadas=self.victimas_rescatadas,
                        victimasPerdidas=self.victimas_perdidas, danoEstructura=self.mapa.dano_estructura)
        return turno_unity(self, agente.id)

    def simular(self):
        while not self.is_terminado():
            self.step()
        return {"semilla": self.semilla, "resultado": self.resultado, "turnos": self.turno,
                "num_agentes": len(self.agentes), "rescatadas": self.victimas_rescatadas,
                "perdidas": self.victimas_perdidas, "tiradas_fuego": self.tiradas_fuego,
                "retiradas": sum(a.retiradas for a in self.agentes),
                "dano_estructura": self.mapa.dano_estructura}


def simular_partidas(n_partidas=50, semilla_base=42, reglas=None):
    if type(n_partidas) is not int or n_partidas < 1:
        raise ValueError("n_partidas debe ser un entero positivo.")
    if type(semilla_base) is not int:
        raise ValueError("semilla_base debe ser un entero.")
    resultados = [FlashPoint(semilla=semilla_base + i, reglas=reglas).simular() for i in range(n_partidas)]
    ganadas = sum(r["resultado"] == "victoria" for r in resultados)
    por_victimas = sum(r["resultado"] == "derrota_victimas" for r in resultados)
    por_colapso = sum(r["resultado"] == "derrota_colapso" for r in resultados)
    return resultados, {"partidas": n_partidas, "ganadas": ganadas, "perdidas": por_victimas + por_colapso,
                         "derrotas_victimas": por_victimas, "derrotas_colapso": por_colapso,
                         "sin_resolver": sum(r["resultado"] == "sin_resolver" for r in resultados),
                         "porcentaje_victorias": 100 * ganadas / n_partidas,
                         "promedio_turnos": sum(r["turnos"] for r in resultados) / n_partidas}
