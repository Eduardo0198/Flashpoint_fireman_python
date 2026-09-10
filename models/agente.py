import heapq
import numpy as np
from mesa import Agent
from models.mapa import PARED, PUERTA_CERRADA, DANO_MAXIMO
from models.pois import SIN_POI, POI_SIN_REVELAR, VICTIMA_REVELADA, PROB_VICTIMA


class Bombero(Agent):
    def __init__(self, model, fila, columna, estrategia="cercano"):
        # Inicializacion de variables y del modelo
        super().__init__(model)
        self.fila = fila
        self.columna = columna
        self.cargando_victima = False
        self.ap = 4
        self.estrategia = estrategia
        self.rescates = 0
        self.celdas_visitadas = 1
        self.paredes_rotas = 0
    # Checa las paredes que se encuentran cerca
    def _valor_borde(self, r1, c1, r2, c2):
        pv, ph = self.model.paredes_verticales, self.model.paredes_horizontales
        if r1 == r2 and abs(c1 - c2) == 1:
            return pv[r1, max(c1, c2)]
        if c1 == c2 and abs(r1 - r2) == 1:
            return ph[max(r1, r2), c1]
        return PARED
    #Inicializamos la matriz de las paredes, puertas y el daño acumulado
    def _dano_borde(self, r1, c1, r2, c2):
        dv, dh = self.model.danos_verticales, self.model.danos_horizontales
        if r1 == r2 and abs(c1 - c2) == 1:
            return dv[r1, max(c1, c2)]
        if c1 == c2 and abs(r1 - r2) == 1:
            return dh[max(r1, r2), c1]
        return 0

    
    def _es_puerta_cerrada(self, r1, c1, r2, c2):
        return self._valor_borde(r1, c1, r2, c2) == PUERTA_CERRADA

    def _es_pared_intacta(self, r1, c1, r2, c2):
        return self._valor_borde(r1, c1, r2, c2) == PARED and self._dano_borde(r1, c1, r2, c2) < DANO_MAXIMO

    def _abrir_puerta(self, r1, c1, r2, c2):
        pv, ph = self.model.paredes_verticales, self.model.paredes_horizontales
        if r1 == r2 and abs(c1 - c2) == 1:
            pv[r1, max(c1, c2)] = 3
        elif c1 == c2 and abs(r1 - r2) == 1:
            ph[max(r1, r2), c1] = 3

    def _golpear_pared(self, r1, c1, r2, c2):
        dv, dh = self.model.danos_verticales, self.model.danos_horizontales
        if r1 == r2 and abs(c1 - c2) == 1:
            limite = max(c1, c2)
            dv[r1, limite] += 1
            destruida = dv[r1, limite] >= DANO_MAXIMO
        else:
            limite = max(r1, r2)
            dh[limite, c1] += 1
            destruida = dh[limite, c1] >= DANO_MAXIMO
        if destruida:
            self.paredes_rotas += 1
        return destruida
    def vecinos(self, r, c):
        alto, ancho = self.model.height, self.model.width
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < alto and 0 <= nc < ancho):
                continue
            if self._es_pared_intacta(r, c, nr, nc):
                continue
            yield nr, nc

    def costo_entrar(self, r_actual, c_actual, r, c):
        costo = 2 if self.model.fuego[r, c] == 2 else 1
        if self._es_puerta_cerrada(r_actual, c_actual, r, c):
            costo += 1
        return costo

    def a_estrella(self, inicio, es_meta):
        frontera = [(0, inicio)]
        costo_acumulado = {inicio: 0}
        padres = {inicio: None}

        while frontera:
            _, actual = heapq.heappop(frontera)
            if es_meta(*actual):
                camino = []
                nodo = actual
                while nodo is not None:
                    camino.append(nodo)
                    nodo = padres[nodo]
                camino.reverse()
                return camino

            for vecino in self.vecinos(*actual):
                nuevo_costo = costo_acumulado[actual] + self.costo_entrar(*actual, *vecino)
                if vecino not in costo_acumulado or nuevo_costo < costo_acumulado[vecino]:
                    costo_acumulado[vecino] = nuevo_costo
                    prioridad = nuevo_costo + self._heuristica(vecino, inicio)
                    heapq.heappush(frontera, (prioridad, vecino))
                    padres[vecino] = actual
        return None

    def _heuristica(self, celda, inicio):
        return abs(celda[0] - inicio[0]) + abs(celda[1] - inicio[1])

    def celda_es_borde(self, r, c):
        alto, ancho = self.model.height, self.model.width
        return r == 0 or c == 0 or r == alto - 1 or c == ancho - 1
    
    def _candidatos_objetivo(self, tipos):
        candidatos = []
        if "poi" in tipos:
            filas, columnas = np.where(
                (self.model.pois == POI_SIN_REVELAR) | (self.model.pois == VICTIMA_REVELADA)
            )
            candidatos += [("poi", (int(r), int(c))) for r, c in zip(filas, columnas)]
        if "fuego" in tipos:
            filas, columnas = np.where(self.model.fuego == 2)
            candidatos += [("fuego", (int(r), int(c))) for r, c in zip(filas, columnas)]
        return candidatos

    def _objetivo_mas_cercano(self, candidatos):
        inicio = (self.fila, self.columna)
        cola = []
        for idx, (tipo, celda) in enumerate(candidatos):
            prioridad = self._heuristica(celda, inicio)
            heapq.heappush(cola, (prioridad, idx, tipo, celda))

        while cola:
            _, _, tipo, celda = heapq.heappop(cola)
            camino = self.a_estrella(inicio, lambda r, c, meta=celda: (r, c) == meta)
            if camino:
                return tipo, camino

        return None, None
    def _pared_hacia_objetivo(self, r_obj, c_obj):
        alto, ancho = self.model.height, self.model.width
        mejor = None
        mejor_dist = None
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = self.fila + dr, self.columna + dc
            if not (0 <= nr < alto and 0 <= nc < ancho):
                continue
            if not self._es_pared_intacta(self.fila, self.columna, nr, nc):
                continue
            dist = abs(nr - r_obj) + abs(nc - c_obj)
            if mejor_dist is None or dist < mejor_dist:
                mejor_dist = dist
                mejor = (nr, nc)
        return mejor

    def encontrar_objetivo(self):
        inicio = (self.fila, self.columna)

        if self.cargando_victima:
            camino = self.a_estrella(inicio, self.celda_es_borde)
            if camino:
                return ("salir", camino)
            objetivo_mas_cercano = (0, 0)
            return ("romper_hacia_salir", objetivo_mas_cercano)
        
        if self.estrategia == "apagafuegos":
            grupos = [["fuego"], ["poi"]]
        else:
            grupos = [["poi", "fuego"]]

        for tipos in grupos:
            candidatos = self._candidatos_objetivo(tipos)
            if not candidatos:
                continue
            tipo, camino = self._objetivo_mas_cercano(candidatos)
            if camino:
                return (tipo, camino)

        objetivos = ["fuego", "poi"] if self.estrategia == "apagafuegos" else ["poi", "fuego"]
        matrices = {"poi": self.model.pois, "fuego": self.model.fuego}

        def _es_objetivo(tipo, valor):
            if tipo == "poi":
                return valor in (POI_SIN_REVELAR, VICTIMA_REVELADA)
            return valor == 2

        posiciones = list(zip(*np.where(np.vectorize(lambda v: _es_objetivo(objetivos[0], v))(matrices[objetivos[0]])))) or \
                     list(zip(*np.where(np.vectorize(lambda v: _es_objetivo(objetivos[1], v))(matrices[objetivos[1]]))))
        if not posiciones:
            return (None, None)

        r_obj, c_obj = min(posiciones, key=lambda p: abs(p[0] - self.fila) + abs(p[1] - self.columna))
        return ("romper_hacia_objetivo", (r_obj, c_obj))

    def moverse_aleatorio(self):
        vecinos_validos = list(self.vecinos(self.fila, self.columna))
        if not vecinos_validos:
            return False
        idx = self.model.random.randrange(len(vecinos_validos))
        siguiente = vecinos_validos[idx]
        costo = self.costo_entrar(self.fila, self.columna, *siguiente)
        if self.ap < costo:
            return False
        if self._es_puerta_cerrada(self.fila, self.columna, *siguiente):
            self._abrir_puerta(self.fila, self.columna, *siguiente)
        self.fila, self.columna = siguiente
        self.ap -= costo
        self.celdas_visitadas += 1
        return True
    def step(self):
        self.ap = 4

        if self.estrategia == "aleatorio":
            while self.ap > 0:
                valor_aqui = self.model.pois[self.fila, self.columna]
                if valor_aqui == POI_SIN_REVELAR:
                    if self.model.random.random() < PROB_VICTIMA:
                        self.model.pois[self.fila, self.columna] = VICTIMA_REVELADA
                        self.cargando_victima = True
                    else:
                        self.model.pois[self.fila, self.columna] = SIN_POI
                elif valor_aqui == VICTIMA_REVELADA:
                    self.model.pois[self.fila, self.columna] = SIN_POI
                    self.cargando_victima = True
                if self.model.fuego[self.fila, self.columna] == 2 and self.ap >= 2:
                    self.model.fuego[self.fila, self.columna] = 0
                    self.ap -= 2
                    continue
                if self.cargando_victima and self.celda_es_borde(self.fila, self.columna):
                    self.cargando_victima = False
                    self.model.victimas_rescatadas += 1
                    self.rescates += 1
                    continue
                if not self.moverse_aleatorio():
                    break
            return

        while self.ap > 0:
            tipo, dato = self.encontrar_objetivo()

            if tipo is None:
                break

            if tipo in ("romper_hacia_objetivo", "romper_hacia_salir"):
                objetivo = dato
                pared = self._pared_hacia_objetivo(*objetivo)
                if pared is None or self.ap < 2:
                    break
                self._golpear_pared(self.fila, self.columna, *pared)
                self.ap -= 2
                continue

            camino = dato
            if len(camino) <= 1:
                if tipo == "poi":
                    valor_actual = self.model.pois[self.fila, self.columna]
                    if valor_actual == POI_SIN_REVELAR:
                        if self.model.random.random() < PROB_VICTIMA:
                            self.model.pois[self.fila, self.columna] = VICTIMA_REVELADA
                            self.cargando_victima = True
                        else:
                            self.model.pois[self.fila, self.columna] = SIN_POI  # falsa alarma
                        continue
                    if valor_actual == VICTIMA_REVELADA:
                        self.model.pois[self.fila, self.columna] = SIN_POI
                        self.cargando_victima = True
                        continue
                    continue
                if tipo == "fuego":
                    if self.ap < 2:
                        break
                    self.model.fuego[self.fila, self.columna] = 0
                    self.ap -= 2
                    continue
                if tipo == "salir":
                    self.cargando_victima = False
                    self.model.victimas_rescatadas += 1
                    self.rescates += 1
                    continue

            siguiente = camino[1]
            costo = self.costo_entrar(self.fila, self.columna, *siguiente)
            if self.ap < costo:
                break
            if self._es_puerta_cerrada(self.fila, self.columna, *siguiente):
                self._abrir_puerta(self.fila, self.columna, *siguiente)
            self.fila, self.columna = siguiente
            self.ap -= costo
            self.celdas_visitadas += 1