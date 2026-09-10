"""Reglas compartidas; las coordenadas de este paquete empiezan en cero."""

from dataclasses import dataclass

FILAS, COLUMNAS = 6, 8
VACIO, HUMO, FUEGO = 0, 1, 2
ABIERTO, PARED, PUERTA_CERRADA, PUERTA_ABIERTA, PARED_DANADA = range(5)
# Código interno: el protocolo exporta las entradas como ABIERTO (0).
ENTRADA = 5
AP_POR_TURNO, MAX_AP_AHORRADOS = 4, 2
COSTOS = {"mover": 1, "fuego": 2, "humo": 1, "poi": 0,
          "recoger": 2, "golpear": 2, "abrir": 1, "cerrar": 1}
PRIORIDADES = {"fuego": 10, "victima": 6, "poi": 6, "humo": 2}
BOLSA_POIS_INICIAL = {"victima": 12, "falsa_alarma": 6}
N_POIS_OBJETIVO = 3
POIS_INICIALES = ((1, 3), (4, 0), (4, 7))
FUEGO_INICIAL = ((0, 6), (3, 2), (4, 1), (0, 4), (1, 1),
                 (1, 5), (5, 0), (0, 7), (1, 0), (5, 3))
ENTRADAS = {
    "arriba": {"exterior": (-1, 5), "interior": (0, 5), "borde": ("horizontal", 0, 5)},
    "izquierda": {"exterior": (2, -1), "interior": (2, 0), "borde": ("vertical", 2, 0)},
    "derecha": {"exterior": (3, 8), "interior": (3, 7), "borde": ("vertical", 3, 8)},
    "abajo": {"exterior": (6, 2), "interior": (5, 2), "borde": ("horizontal", 6, 2)},
}
ENTRADAS_AGENTES = ("izquierda", "derecha", "abajo", "arriba", "izquierda", "derecha")
DIRECCIONES = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class Reglas:
    victimas_para_ganar: int = 7
    victimas_para_perder: int = 4
    # 24 procede del modelo anterior del repositorio. None desactiva el colapso.
    dano_para_colapso: int | None = 24
    max_turnos: int = 300

    def __post_init__(self):
        for campo in ("victimas_para_ganar", "victimas_para_perder", "max_turnos", "dano_para_colapso"):
            valor = getattr(self, campo)
            if campo == "dano_para_colapso" and valor is None:
                continue
            if type(valor) is not int or valor < 1:
                raise ValueError(f"{campo} debe ser un entero positivo.")
