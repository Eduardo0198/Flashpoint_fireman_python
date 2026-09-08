from mesa import Model
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
from models.fuego import crear_matriz_fuego, advance_fire, ROWS_FUEGO, COLS_FUEGO
from models.pois import crear_matriz_pois, POI_SIN_REVELAR, VICTIMA_REVELADA, SIN_POI, PROB_VICTIMA
from models.mapa import crear_paredes, crear_danos, PARED, DANO_MAXIMO
from models.agente import Bombero

VICTIMAS_PARA_GANAR = 7
VICTIMAS_PARA_PERDER = 4
DANO_PARA_COLAPSO = 24
POIS_EN_TABLERO = 3

MAX_AGENTES = 6

class FlashPoint(Model):
    def __init__(self, width=COLS_FUEGO, height=ROWS_FUEGO,
                 num_agentes=1, estrategia="cercano", **kwargs):
        super().__init__()
        self.width = width
        self.height = height
        self.grid = SingleGrid(self.width, self.height, torus=False)
        self.paredes_verticales, self.paredes_horizontales = crear_paredes()
        self.danos_verticales, self.danos_horizontales = crear_danos()

        self.fuego = crear_matriz_fuego()
        self.pois = crear_matriz_pois()
        self.turno = 0
        self.victimas_rescatadas = 0
        self.victimas_perdidas = 0
        self.dano_total = 0
        self.resultado = None  # None mientras juega; luego "victoria", "derrota_victimas", "derrota_colapso"

        for _ in range(num_agentes):
            Bombero(self, fila=0, columna=0, estrategia=estrategia)

        self.datacollector = DataCollector(
            model_reporters={
                "Turno": lambda m: m.turno,
                "Rescatadas": lambda m: m.victimas_rescatadas,
                "Perdidas": lambda m: m.victimas_perdidas,
                "DanoTotal": lambda m: m.dano_total,
                "Terminado": lambda m: m.is_terminado(),
                "Resultado": lambda m: m.resultado,
                "num_agentes": lambda m: len(m.agents),
            },
            agent_reporters={
                "Rescates": lambda a: a.rescates,
                "CeldasVisitadas": lambda a: a.celdas_visitadas,
                "ParedesRotas": lambda a: a.paredes_rotas,
            },
        )
    def is_terminado(self):
        return self.resultado is not None

    def _revisar_fin_de_juego(self):
        if self.victimas_rescatadas >= VICTIMAS_PARA_GANAR:
            self.resultado = "victoria"
        elif self.victimas_perdidas >= VICTIMAS_PARA_PERDER:
            self.resultado = "derrota_victimas"
        elif self.dano_total >= DANO_PARA_COLAPSO:
            self.resultado = "derrota_colapso"
    def _resolver_pois_en_fuego(self):
        filas, columnas = (self.fuego == 2).nonzero()
        for r, c in zip(filas, columnas):
            valor = self.pois[r, c]
            if valor == SIN_POI:
                continue
            if valor == POI_SIN_REVELAR:
                # Se revela al perderse: solo cuenta como víctima perdida si en verdad lo era.
                if self.random.random() < PROB_VICTIMA:
                    self.victimas_perdidas += 1
            elif valor == VICTIMA_REVELADA:
                self.victimas_perdidas += 1
            self.pois[r, c] = SIN_POI
    def _reponer_pois(self):
        activos = (self.pois != SIN_POI).sum()
        intentos = 0
        while activos < POIS_EN_TABLERO and intentos < 200:
            intentos += 1
            r = self.random.randrange(self.height)
            c = self.random.randrange(self.width)
            if self.pois[r, c] != SIN_POI:
                continue
            if self.fuego[r, c] == 2:
                continue  
            self.pois[r, c] = POI_SIN_REVELAR
            activos += 1

    def step(self):
        if self.is_terminado():
            return

        self.agents.shuffle_do("step")

        _, _, dano_nuevo = advance_fire(
            self.fuego, self.paredes_verticales, self.paredes_horizontales,
            self.danos_verticales, self.danos_horizontales, self.random,
        )
        self.dano_total += dano_nuevo

        self._resolver_pois_en_fuego()
        self._reponer_pois()

        self.turno += 1
        self._revisar_fin_de_juego()
        self.datacollector.collect(self)

    def to_dict(self):
        return {
            "turno": self.turno,
            "width": self.width,
            "height": self.height,
            "fuego": self.fuego.flatten().tolist(),
            "pois": self.pois.flatten().tolist(),
            "paredes_verticales": self.paredes_verticales.flatten().tolist(),
            "paredes_horizontales": self.paredes_horizontales.flatten().tolist(),
            "danos_verticales": self.danos_verticales.flatten().tolist(),
            "danos_horizontales": self.danos_horizontales.flatten().tolist(),
            "victimas_rescatadas": self.victimas_rescatadas,
            "victimas_perdidas": self.victimas_perdidas,
            "dano_total": self.dano_total,
            "resultado": self.resultado,
            "agentes": [
                {"id": b.unique_id, "x": b.columna, "y": b.fila, "cargando_victima": b.cargando_victima}
                for b in self.agents
            ],
        }