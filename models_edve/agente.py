"""Spartans con A*, utilidad, reservas de Cortana y presupuesto individual de AP."""

import heapq

from .config import (AP_POR_TURNO, COSTOS, FUEGO, HUMO, MAX_AP_AHORRADOS,
                     PARED, PARED_DANADA, PUERTA_ABIERTA, PUERTA_CERRADA, VACIO)


def es_celda_segura(model, posicion):
    if model.mapa.es_interior(posicion):
        return model.fuego[posicion] != FUEGO
    return any(posicion == e["exterior"] for e in model.mapa.entradas.values())


def puede_apagar_desde(model, origen, objetivo):
    if not es_celda_segura(model, origen) or not model.mapa.es_interior(objetivo):
        return False
    if origen == objetivo:
        return model.fuego[objetivo] == HUMO
    return model.mapa.puede_pasar(origen, objetivo, exterior=True)


def a_estrella(model, inicio, destino):
    if not es_celda_segura(model, inicio) or not es_celda_segura(model, destino):
        return [], float("inf")

    def h(pos):
        return abs(pos[0] - destino[0]) + abs(pos[1] - destino[1])

    frontera = [(h(inicio), 0, inicio)]
    costos, padres = {inicio: 0}, {inicio: None}
    while frontera:
        _, costo, actual = heapq.heappop(frontera)
        if costo != costos[actual]:
            continue
        if actual == destino:
            camino = []
            while actual is not None:
                camino.append(actual)
                actual = padres[actual]
            return camino[::-1], costo
        for vecino in model.mapa.vecinos(actual):
            if not es_celda_segura(model, vecino):
                continue
            nuevo = costo + COSTOS["mover"] + model.mapa.costo_preparacion(actual, vecino)
            if nuevo < costos.get(vecino, float("inf")):
                costos[vecino], padres[vecino] = nuevo, actual
                heapq.heappush(frontera, (nuevo + h(vecino), nuevo, vecino))
    return [], float("inf")


def ruta_hacia_tarea(model, inicio, tarea):
    objetivo = tarea["posicion"]
    if tarea["tipo"] not in ("fuego", "humo"):
        return a_estrella(model, inicio, objetivo)
    posiciones = list(model.mapa.vecinos(objetivo))
    if tarea["tipo"] == "humo":
        posiciones.append(objetivo)
    mejor_camino, mejor_costo = [], float("inf")
    for posicion in posiciones:
        camino, costo = a_estrella(model, inicio, posicion)
        if not camino:
            continue
        if posicion != objetivo:
            costo += model.mapa.costo_preparacion(posicion, objetivo)
        if costo < mejor_costo:
            mejor_camino, mejor_costo = camino, costo
    return mejor_camino, mejor_costo


class Bombero:
    def __init__(self, model, identificador, entrada):
        self.model = model
        self.id = identificador
        self.entrada = entrada
        self.posicion = model.mapa.entradas[entrada]["exterior"]
        self.ap = 0
        self.ap_guardados = 0
        self.tarea_id = None
        self.victima_id = None
        self.rescates = 0
        self.retiradas = 0

    def registrar(self, tipo, costo=0, **datos):
        self.model.emitir(tipo, **{
            "agenteId": self.id, "row": int(self.posicion[0]), "col": int(self.posicion[1]),
            "costoAP": costo, "actionPoints": self.ap, "apGuardados": self.ap_guardados,
            "cargandoVictima": self.victima_id is not None, "tareaId": self.tarea_id or 0, **datos,
        })

    def pagar(self, accion):
        costo = COSTOS[accion]
        if self.ap < costo:
            return False
        self.ap -= costo
        return True

    def iniciar_turno(self):
        self.ap = AP_POR_TURNO + min(self.ap_guardados, MAX_AP_AHORRADOS)
        self.ap_guardados = 0
        self.registrar("agente_inicia_turno")

    def ahorrar_puntos(self):
        self.ap_guardados = min(self.ap, MAX_AP_AHORRADOS)
        descartados = self.ap - self.ap_guardados
        self.ap = 0
        self.registrar("agente_ahorra_ap", descartados=descartados)

    def evaluar_tareas(self):
        opciones = []
        for tarea in self.model.cortana.tareas:
            if tarea["estado"] != "disponible":
                continue
            camino, costo = ruta_hacia_tarea(self.model, self.posicion, tarea)
            if camino:
                opciones.append({"id": tarea["id"], "costo": costo,
                                 "utilidad": tarea["prioridad"] / (costo + 1)})
        return sorted(opciones, key=lambda x: (-x["utilidad"], x["costo"], x["id"]))

    def elegir_tarea(self):
        cortana = self.model.cortana
        reservada = cortana.buscar_tarea(self.tarea_id)
        if reservada is not None:
            return reservada
        opciones = self.evaluar_tareas()
        if not opciones:
            return None
        mejor = opciones[0]
        tarea = cortana.buscar_tarea(mejor["id"])
        tarea.update(estado="asignada", agente=self.id)
        self.tarea_id = tarea["id"]
        self.registrar("agente_asigna_tarea", tipoTarea=tarea["tipo"],
                       objetivoRow=tarea["posicion"][0], objetivoCol=tarea["posicion"][1],
                       utilidad=mejor["utilidad"], costoRuta=mejor["costo"])
        return tarea

    def liberar_tarea(self, tarea, motivo):
        tarea.update(estado="disponible", agente=None)
        self.tarea_id = None
        self.registrar("agente_libera_tarea", tareaLiberadaId=tarea["id"], motivo=motivo)

    def cambiar_puerta(self, vecino, abrir):
        mapa = self.model.mapa
        if vecino not in mapa.vecinos(self.posicion):
            return False
        vertical, indice = mapa.borde_entre(self.posicion, vecino)
        matriz = mapa.matriz(vertical)
        accion = "abrir" if abrir else "cerrar"
        if matriz[indice] != (PUERTA_CERRADA if abrir else PUERTA_ABIERTA) or not self.pagar(accion):
            return False
        matriz[indice] = PUERTA_ABIERTA if abrir else PUERTA_CERRADA
        self.registrar("agente_abre_puerta" if abrir else "agente_cierra_puerta", COSTOS[accion],
                       row=indice[0], col=indice[1], esVertical=vertical, estadoNuevo=int(matriz[indice]))
        self.model.gameMasterCortana()
        return True

    def abrir_puerta(self, vecino):
        return self.cambiar_puerta(vecino, True)

    def cerrar_puerta(self, vecino):
        return self.cambiar_puerta(vecino, False)

    def avanzar(self, destino):
        mapa = self.model.mapa
        if self.model.evaluar_resultado() is not None or destino not in mapa.vecinos(self.posicion):
            return False
        estado = mapa.estado_entre(self.posicion, destino)
        if estado == PUERTA_CERRADA:
            return self.abrir_puerta(destino)
        if estado in (PARED, PARED_DANADA):
            if not self.pagar("golpear"):
                return False
            cambio = mapa.danar_pared(self.posicion, destino)
            tipo = "agente_dana_pared" if cambio["estadoNuevo"] == PARED_DANADA else "agente_derriba_pared"
            self.registrar(tipo, COSTOS["golpear"], **cambio)
        else:
            if (not es_celda_segura(self.model, destino)
                    or not mapa.puede_pasar(self.posicion, destino, exterior=True)
                    or not self.pagar("mover")):
                return False
            origen = self.posicion
            self.posicion = destino
            self.registrar("agente_mueve", COSTOS["mover"], origenRow=origen[0], origenCol=origen[1])
        self.model.gameMasterCortana()
        return True

    def realizar_objetivo(self, tarea):
        m, tipo = self.model, tarea["tipo"]
        objetivo = tarea["posicion"]
        al_alcance = (puede_apagar_desde(m, self.posicion, objetivo)
                      if tipo in ("fuego", "humo") else self.posicion == objetivo)
        if (tarea["agente"] != self.id or tarea["estado"] != "asignada"
                or tarea["fase"] != "objetivo" or not al_alcance or self.victima_id is not None):
            return False
        accion = "recoger" if tipo == "victima" else tipo
        if not self.pagar(accion):
            return False
        datos = {"row": objetivo[0], "col": objetivo[1], "objetivoTareaId": tarea["id"]}
        if tipo in ("fuego", "humo"):
            m.fuego[objetivo] = VACIO
            m.cortana.cerrar_tarea(tarea, "completada", f"S{self.id} retiró {tipo}")
            evento = "agente_apaga_fuego" if tipo == "fuego" else "agente_apaga_humo"
            datos["estadoNuevo"] = VACIO
        elif tipo == "poi":
            m.pois_revelado[objetivo] = True
            valor = int(m.pois[objetivo])
            datos.update(tipoPoi=valor, revelado=True, retirado=valor == 1)
            if valor == 1:
                m.pois[objetivo] = 0
            m.cortana.cerrar_tarea(tarea, "completada", "POI revelado")
            evento = "agente_revela_poi"
        else:
            m.pois[objetivo] = 0
            m.pois_revelado[objetivo] = False
            self.victima_id = tarea["id"]
            tarea["fase"] = "traslado"
            evento = "agente_recoge_victima"
        self.registrar(evento, COSTOS[accion], **datos)
        m.gameMasterCortana()
        return True

    def trasladar_victima(self, tarea):
        m = self.model
        if self.victima_id != tarea["id"] or tarea["fase"] != "traslado" or tarea["agente"] != self.id:
            return False
        salidas = [a_estrella(m, self.posicion, e["exterior"]) for e in m.mapa.entradas.values()]
        camino, _ = min(salidas, key=lambda ruta: ruta[1])
        if not camino:
            return False
        if len(camino) > 1:
            return self.avanzar(camino[1])
        self.victima_id = None
        self.rescates += 1
        m.victimas_rescatadas += 1
        m.cortana.cerrar_tarea(tarea, "completada", f"Víctima rescatada por S{self.id}")
        self.registrar("victima_rescatada", victimasRescatadas=m.victimas_rescatadas)
        m.gameMasterCortana()
        return True

    def retirarse_por_fuego(self):
        m = self.model
        if es_celda_segura(m, self.posicion):
            return
        origen = self.posicion
        tarea = m.cortana.buscar_tarea(self.tarea_id)
        llevaba_victima = self.victima_id is not None
        if llevaba_victima:
            m.cortana.cerrar_tarea(m.cortana.buscar_tarea(self.victima_id), "cancelada", "Víctima perdida por fuego")
            self.victima_id = None
            m.victimas_perdidas += 1
            self.registrar("victima_perdida", victimasPerdidas=m.victimas_perdidas, enBrazos=True)
        elif tarea is not None:
            self.liberar_tarea(tarea, "El Spartan fue alcanzado por el fuego")
        self.posicion = m.mapa.entradas[self.entrada]["exterior"]
        self.retiradas += 1
        self.registrar("agente_retirada", origenRow=origen[0], origenCol=origen[1],
                       entrada=self.entrada, victimaPerdida=llevaba_victima)

    def step(self, ahorrar=False):
        m = self.model
        if m.evaluar_resultado() is not None:
            return
        self.iniciar_turno()
        if not ahorrar:
            while m.evaluar_resultado() is None:
                m.gameMasterCortana()
                tarea = m.cortana.buscar_tarea(self.tarea_id)
                if tarea is None:
                    if self.ap == 0:
                        break
                    tarea = self.elegir_tarea()
                if tarea is None:
                    break
                if self.victima_id is not None:
                    pudo_actuar = self.trasladar_victima(tarea)
                else:
                    camino, _ = ruta_hacia_tarea(m, self.posicion, tarea)
                    if not camino:
                        self.liberar_tarea(tarea, "No hay una ruta segura al objetivo")
                        continue
                    if len(camino) > 1:
                        pudo_actuar = self.avanzar(camino[1])
                    elif tarea["tipo"] in ("fuego", "humo") and not puede_apagar_desde(m, self.posicion, tarea["posicion"]):
                        pudo_actuar = self.avanzar(tarea["posicion"])
                    else:
                        pudo_actuar = self.realizar_objetivo(tarea)
                if not pudo_actuar:
                    break
        self.ahorrar_puntos()
