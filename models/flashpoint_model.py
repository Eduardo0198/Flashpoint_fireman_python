from mesa import Model
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector
from models.fuego import crear_matriz_fuego, advance_fire, ROWS_FUEGO, COLS_FUEGO
from models.pois import crear_matriz_pois
from models.mapa import crear_paredes

class FlashPoint(Model):
    def __init__(self, **kwargs):
        super().__init__()
        self.width = COLS_FUEGO
        self.height = ROWS_FUEGO
        self.grid = SingleGrid(self.width, self.height, torus=False)
        self.paredes_verticales, self.paredes_horizontales = crear_paredes()

        self.fuego = crear_matriz_fuego()
        self.pois = crear_matriz_pois()
        self.turno = 0

        self.datacollector = DataCollector(model_reporters={"Grid": self._get_grid})

    def _get_grid(self):
        grid = self.fuego.copy()
        for content, (x, y) in self.grid.coord_iter():
            if content is not None:
                grid[y][x] = 7
        return grid

    def step(self):
        advance_fire(self.fuego)
        self.turno += 1
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
            "agentes": [
                {"id": a.unique_id, "x": a.pos[0], "y": a.pos[1]}
                for a in self.agents
            ] if hasattr(self, "agents") else []
        }