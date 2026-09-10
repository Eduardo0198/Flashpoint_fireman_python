"""Regresión de reglas, aislamiento de partidas y reconstrucción visual del protocolo."""

import contextlib
from copy import deepcopy
import heapq
import io
import json
import os
from pathlib import Path
import random
import unittest

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np

from models_edve import FlashPoint
from models_edve.agente import a_estrella, puede_apagar_desde, ruta_hacia_tarea
from models_edve.config import (ABIERTO, ENTRADA, FUEGO, HUMO, PARED, PARED_DANADA,
                                PUERTA_ABIERTA, PUERTA_CERRADA, Reglas)
from models_edve.fuego import avanzar_fuego, explosion, flashover
from models_edve.pois import reponer_pois


def escenario():
    m = FlashPoint(reglas=Reglas(dano_para_colapso=None))
    m.fuego.fill(0)
    m.pois.fill(0)
    m.pois_revelado.fill(False)
    m.mapa.verticales[:, 1:-1] = ABIERTO
    m.mapa.horizontales[1:-1, :] = ABIERTO
    m.cortana.tareas.clear()
    m.cortana.ultimo_escaneo.clear()
    m.gameMasterCortana()
    m.eventos.clear()
    return m


def reservar(m, a, tipo, posicion):
    m.gameMasterCortana()
    t = next(t for t in m.cortana.tareas if t["tipo"] == tipo and t["posicion"] == posicion)
    t.update(estado="asignada", agente=a.id)
    a.tarea_id = t["id"]
    return t


def aplicar_eventos(estado, mensaje):
    """Cliente de prueba: reconstruye capas y agentes sin leer estadoFinal."""
    s = deepcopy(estado)
    for e in mensaje["eventos"]:
        tipo = e["tipo"]
        a = next((a for a in s["agentes"] if a["id"] == e.get("agenteId")), None)
        if a is not None:
            for campo in ("actionPoints", "apGuardados", "cargandoVictima"):
                a[campo] = e[campo]
        if tipo in ("agente_mueve", "agente_retirada"):
            a["x"], a["y"] = e["col"], e["row"]
        if tipo in ("humo_cae", "fuego_aparece", "agente_apaga_fuego", "agente_apaga_humo"):
            s["tablero"][e["row"] * 8 + e["col"]] = e["estadoNuevo"]
        if tipo in ("agente_abre_puerta", "agente_cierra_puerta", "agente_dana_pared", "agente_derriba_pared"):
            clave, stride = ("paredesVerticales", 9) if e["esVertical"] else ("paredesHorizontales", 8)
            s[clave][e["row"] * stride + e["col"]] = e["estadoNuevo"]
            s["danoEstructura"] = e.get("danoEstructura", s["danoEstructura"])
        if tipo == "explosion":
            for paso in e["pasos"]:
                if paso["esPared"]:
                    clave, stride = ("paredesVerticales", 9) if paso["esVertical"] else ("paredesHorizontales", 8)
                    s[clave][paso["row"] * stride + paso["col"]] = paso["estadoNuevo"]
                    s["danoEstructura"] = paso["danoEstructura"]
                else:
                    s["tablero"][paso["row"] * 8 + paso["col"]] = paso["estadoNuevo"]
        if tipo == "poi_cae":
            indice = e["row"] * 8 + e["col"]
            s["pois"][indice], s["poisRevelado"][indice] = e["tipoPoi"], False
            if e["apagaFuego"]:
                s["tablero"][indice] = 0
        if tipo == "agente_revela_poi":
            indice = e["row"] * 8 + e["col"]
            s["poisRevelado"][indice] = True
            if e["retirado"]:
                s["pois"][indice] = 0
        if tipo == "agente_recoge_victima":
            indice = e["row"] * 8 + e["col"]
            s["pois"][indice], s["poisRevelado"][indice] = 0, False
        if tipo in ("victima_perdida", "falsa_alarma_quemada"):
            s["victimasPerdidas"] = e["victimasPerdidas"]
            if not e["enBrazos"]:
                indice = e["row"] * 8 + e["col"]
                s["pois"][indice], s["poisRevelado"][indice] = 0, True
        if tipo == "victima_rescatada":
            s["victimasRescatadas"] = e["victimasRescatadas"]
    return s


class ReglasTests(unittest.TestCase):
    def test_mapa_y_entradas_serializadas(self):
        m = FlashPoint()
        s = m.to_dict()
        for clave, longitud in (("tablero", 48), ("pois", 48), ("poisRevelado", 48),
                                ("paredesVerticales", 54), ("paredesHorizontales", 56)):
            self.assertEqual(len(s[clave]), longitud)
        self.assertEqual([a["id"] for a in s["agentes"]], list(range(1, 7)))
        self.assertEqual((s["agentes"][0]["x"], s["agentes"][0]["y"]), (-1, 2))
        self.assertNotIn(4, s["paredesVerticales"] + s["paredesHorizontales"])
        for e in m.mapa.entradas.values():
            orientacion, r, c = e["borde"]
            vertical = orientacion == "vertical"
            self.assertEqual(m.mapa.matriz(vertical)[r, c], ENTRADA)
            clave, stride = ("paredesVerticales", 9) if vertical else ("paredesHorizontales", 8)
            self.assertEqual(s[clave][r * stride + c], ABIERTO)
        self.assertEqual(sum(s["poisRevelado"]), 0)

    def test_dos_golpes_de_dos_ap_y_movimiento_aparte(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion = (2, 2)
        m.mapa.verticales[2, 3] = PARED
        a.iniciar_turno()
        self.assertTrue(a.avanzar((2, 3)))
        self.assertEqual((a.ap, m.mapa.verticales[2, 3], m.mapa.dano_estructura), (2, PARED_DANADA, 1))
        self.assertFalse(m.mapa.puede_pasar((2, 2), (2, 3)))
        a.ahorrar_puntos()
        a.iniciar_turno()
        self.assertEqual(a.ap, 6)
        self.assertTrue(a.avanzar((2, 3)))
        self.assertEqual((a.ap, a.posicion, m.mapa.dano_estructura), (4, (2, 2), 2))
        self.assertEqual(m.mapa.verticales[2, 3], ABIERTO)
        self.assertTrue(a.avanzar((2, 3)))
        self.assertEqual((a.ap, a.posicion), (3, (2, 3)))

    def test_golpe_sin_ap_no_cambia_pared(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 2), 1
        m.mapa.verticales[2, 3] = PARED
        self.assertFalse(a.avanzar((2, 3)))
        self.assertEqual((a.ap, m.mapa.dano_estructura), (1, 0))

    def test_astar_considera_dos_golpes_y_no_atraviesa_fuego(self):
        m = escenario()
        m.fuego.fill(FUEGO)
        m.fuego[2, 2:4] = 0
        m.mapa.verticales[2, 3] = PARED
        self.assertEqual(a_estrella(m, (2, 2), (2, 3))[1], 5)
        m.mapa.danar_pared((2, 2), (2, 3))
        self.assertEqual(a_estrella(m, (2, 2), (2, 3))[1], 3)
        m.mapa.danar_pared((2, 2), (2, 3))
        self.assertEqual(a_estrella(m, (2, 2), (2, 3))[1], 1)
        self.assertEqual(a_estrella(m, (2, 2), (2, 4))[0], [])

    def test_explosion_llega_hasta_pared_y_la_dana(self):
        m = escenario()
        m.mapa.verticales[2, 5] = PARED
        m.fuego[2, 2] = FUEGO
        explosion(m, (2, 2))
        self.assertEqual(m.fuego[2, 4], FUEGO)
        self.assertEqual(m.fuego[2, 5], 0)
        self.assertEqual(m.fuego[1, 3], 0)  # no gira en las esquinas
        self.assertEqual(m.mapa.verticales[2, 5], PARED_DANADA)
        explosion(m, (2, 2))
        self.assertEqual(m.mapa.verticales[2, 5], ABIERTO)
        self.assertEqual(m.fuego[2, 5], 0)  # el impacto destructor también se detiene
        explosion(m, (2, 2))
        self.assertEqual(m.fuego[2, 7], FUEGO)

    def test_puerta_cerrada_bloquea_explosion_y_flashover(self):
        m = escenario()
        m.mapa.verticales[2, 3] = PUERTA_CERRADA
        m.fuego[2, 2], m.fuego[2, 3] = FUEGO, HUMO
        explosion(m, (2, 2))
        flashover(m)
        self.assertEqual(m.fuego[2, 3], HUMO)
        self.assertEqual(m.mapa.verticales[2, 3], PUERTA_CERRADA)
        m.mapa.verticales[2, 3] = PUERTA_ABIERTA
        flashover(m)
        self.assertEqual(m.fuego[2, 3], FUEGO)

    def test_apagar_desde_vecina_humo_propio_y_puerta_un_ap(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 2), 6
        m.fuego[2, 3] = FUEGO
        m.mapa.verticales[2, 3] = PUERTA_CERRADA
        t = reservar(m, a, "fuego", (2, 3))
        self.assertFalse(a.realizar_objetivo(t))
        self.assertTrue(a.abrir_puerta((2, 3)))
        self.assertEqual(a.ap, 5)
        self.assertTrue(a.realizar_objetivo(t))
        self.assertEqual((a.ap, a.posicion, m.fuego[2, 3]), (3, (2, 2), 0))
        self.assertTrue(a.cerrar_puerta((2, 3)))
        self.assertEqual(a.ap, 2)
        m.fuego[2, 2] = HUMO
        t = reservar(m, a, "humo", (2, 2))
        self.assertTrue(a.realizar_objetivo(t))
        self.assertEqual(a.ap, 1)
        self.assertFalse(puede_apagar_desde(m, (2, 2), (1, 3)))

    def test_humo_transitable_fuego_no(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 2), 4
        m.fuego[2, 3], m.fuego[2, 4] = HUMO, FUEGO
        self.assertTrue(a.avanzar((2, 3)))
        self.assertFalse(a.avanzar((2, 4)))
        self.assertEqual((a.posicion, a.ap), ((2, 3), 3))
        a.retirarse_por_fuego()
        self.assertEqual(a.posicion, (2, 3))

    def test_cortana_reserva_y_actualiza_prioridad(self):
        m = escenario()
        m.fuego[2, 2] = HUMO
        m.gameMasterCortana()
        a, b = m.agentes[:2]
        t = a.elegir_tarea()
        self.assertIsNone(b.elegir_tarea())
        m.fuego[2, 2] = FUEGO
        m.gameMasterCortana()
        self.assertEqual((t["tipo"], t["prioridad"], t["agente"]), ("fuego", 10, a.id))
        self.assertEqual(len(m.cortana.tareas), 1)
        m.fuego[2, 2] = 0
        m.gameMasterCortana()
        self.assertEqual(m.cortana.tareas, [])
        self.assertIsNone(a.tarea_id)

    def test_utilidad_no_revela_poi_oculto(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion = (2, 2)
        m.fuego[2, 3], m.pois[2, 2] = FUEGO, 2
        m.gameMasterCortana()
        opciones = a.evaluar_tareas()
        self.assertEqual(opciones[0]["utilidad"], 10)
        self.assertEqual(opciones[1]["utilidad"], 6)
        self.assertEqual({t["tipo"] for t in m.cortana.tareas}, {"poi", "fuego"})

    def test_recoger_dos_ap_entregar_fuera_y_perder_una_sola_vez(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 0), 4
        m.pois[2, 0] = 2
        poi = reservar(m, a, "poi", (2, 0))
        self.assertTrue(a.realizar_objetivo(poi))
        self.assertEqual(a.ap, 4)
        victima = reservar(m, a, "victima", (2, 0))
        self.assertTrue(a.realizar_objetivo(victima))
        self.assertEqual(a.ap, 2)
        self.assertTrue(a.trasladar_victima(victima))
        self.assertEqual(a.posicion, (2, -1))
        self.assertTrue(a.trasladar_victima(victima))
        self.assertEqual((a.ap, m.victimas_rescatadas), (1, 1))
        a.posicion, a.ap, a.ap_guardados = (3, 2), 2, 2
        m.pois[3, 2], m.pois_revelado[3, 2] = 2, True
        t = reservar(m, a, "victima", (3, 2))
        a.realizar_objetivo(t)
        m.fuego[3, 2] = FUEGO
        a.retirarse_por_fuego()
        a.retirarse_por_fuego()
        self.assertEqual((a.posicion, a.ap_guardados, m.victimas_perdidas), ((2, -1), 2, 1))
        self.assertIsNone(a.victima_id)
        self.assertIsNone(m.cortana.buscar_tarea(t["id"]))

    def test_bolsa_finita_y_poi_limpia_riesgo(self):
        m = FlashPoint()
        self.assertEqual(m.bolsa_pois["victima"] + int(np.count_nonzero(m.pois == 2)), 12)
        self.assertEqual(m.bolsa_pois["falsa_alarma"] + int(np.count_nonzero(m.pois == 1)), 6)
        m.pois.fill(0)
        m.fuego.fill(FUEGO)
        m.bolsa_pois = {"victima": 1, "falsa_alarma": 0}
        reponer_pois(m)
        self.assertEqual(np.count_nonzero(m.pois), 1)
        self.assertEqual(m.fuego[m.pois != 0].tolist(), [0])
        reponer_pois(m)
        self.assertEqual(np.count_nonzero(m.pois), 1)

    def test_humo_en_fuego_dispara_explosion_y_perdida_distante(self):
        m = escenario()
        m.fuego[2, 2], m.pois[2, 6] = FUEGO, 2
        class Dados:
            def randint(self, minimo, maximo):
                return 2
        m.random = Dados()
        avanzar_fuego(m)
        self.assertEqual([e["tipo"] for e in m.eventos][:2], ["tirar_dados", "explosion"])
        self.assertEqual(m.eventos[0]["dado1"], 3)
        self.assertEqual(m.victimas_perdidas, 1)
        self.assertEqual(m.pois[2, 6], 0)

    def test_un_agente_y_un_fuego_incluso_al_ahorrar(self):
        m = FlashPoint()
        for esperado in (1, 2, 3, 4, 5, 6, 1):
            payload = m.step(ahorrar=True)
            inicios = [e for e in payload["eventos"] if e["tipo"] == "agente_inicia_turno"]
            self.assertEqual([e["agenteId"] for e in inicios], [esperado])
            tiradas = [e for e in payload["eventos"] if e["tipo"] == "tirar_dados" and e["proposito"] == "fuego"]
            self.assertEqual(len(tiradas), 1)
        self.assertEqual(inicios[0]["actionPoints"], 6)
        self.assertEqual(m.agentes[0].ap_guardados, 2)

    def test_colapso_por_hachazo_termina_sin_tirar_fuego(self):
        m = escenario()
        m.reglas = Reglas(dano_para_colapso=1)
        a = m.agentes[0]
        a.posicion = (2, 2)
        m.mapa.verticales[2, 3] = PARED
        # El único sitio seguro para atender el fuego requiere golpear esa pared.
        m.fuego.fill(FUEGO)
        m.fuego[2, 2] = 0
        for dr, dc in ((-1, 0), (1, 0), (0, -1)):
            v, indice = m.mapa.borde_entre(a.posicion, (2 + dr, 2 + dc))
            m.mapa.matriz(v)[indice] = PARED
        reservar(m, a, "fuego", (2, 3))
        payload = m.step()
        self.assertEqual(m.resultado, "derrota_colapso")
        self.assertEqual(m.tiradas_fuego, 0)
        self.assertEqual(payload["eventos"][-1]["tipo"], "partida_terminada")
        anterior = m.to_dict()
        self.assertEqual(m.step()["eventos"], [])
        self.assertEqual(m.to_dict(), anterior)

    def test_colapso_explosion_detiene_al_agotar_marcas(self):
        m = escenario()
        m.reglas = Reglas(dano_para_colapso=1)
        explosion(m, (2, 2))
        self.assertEqual(m.mapa.dano_estructura, 1)
        self.assertEqual(m.evaluar_resultado(), "derrota_colapso")

    def test_rescate_ganador_termina_antes_del_fuego(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 0), 2
        m.pois[2, 0], m.pois_revelado[2, 0] = 2, True
        tarea = reservar(m, a, "victima", (2, 0))
        a.realizar_objetivo(tarea)
        m.victimas_rescatadas = 6
        mensaje = m.step()
        self.assertEqual(m.resultado, "victoria")
        self.assertEqual(m.victimas_rescatadas, 7)
        self.assertEqual(m.tiradas_fuego, 0)
        self.assertTrue(mensaje["estadoFinal"]["terminado"])

    def test_explosion_y_hachazo_comparten_marcas(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion, a.ap = (2, 3), 2
        m.mapa.verticales[2, 3] = PARED
        m.fuego[2, 2] = FUEGO
        explosion(m, (2, 2))
        antes = m.mapa.dano_estructura
        self.assertEqual(m.mapa.verticales[2, 3], PARED_DANADA)
        self.assertTrue(a.avanzar((2, 2)))
        self.assertEqual(m.mapa.verticales[2, 3], ABIERTO)
        self.assertEqual(m.mapa.dano_estructura, antes + 1)
        self.assertEqual(a.posicion, (2, 3))
        self.assertEqual(a.ap, 0)

    def test_reserva_continua_entre_turnos_con_pared_parcial(self):
        m = escenario()
        a = m.agentes[0]
        a.posicion = (2, 2)
        m.fuego.fill(FUEGO)
        m.fuego[2, 2] = 0
        m.mapa.verticales[2, 3] = PARED
        tarea = reservar(m, a, "fuego", (2, 3))
        a.step()
        self.assertEqual(m.mapa.verticales[2, 3], ABIERTO)
        self.assertEqual(m.fuego[2, 3], FUEGO)
        self.assertEqual(a.tarea_id, tarea["id"])
        self.assertEqual(tarea["estado"], "asignada")
        a.step()
        self.assertEqual(m.fuego[2, 3], 0)
        self.assertIsNone(m.cortana.buscar_tarea(tarea["id"]))

    def test_semillas_y_partidas_independientes(self):
        a, b, otro = FlashPoint(17), FlashPoint(17), FlashPoint(18)
        for _ in range(8):
            esperado = b.step()
            otro.step()
            self.assertEqual(a.step(), esperado)
        snapshot = a.to_dict()
        snapshot["tablero"][0] = 999
        self.assertNotEqual(a.to_dict()["tablero"][0], 999)

    def test_reconstruccion_eventos_y_conservacion_en_partidas(self):
        claves = ("tablero", "pois", "poisRevelado", "paredesVerticales", "paredesHorizontales",
                  "victimasRescatadas", "victimasPerdidas", "danoEstructura")
        for semilla in range(42, 52):
            m = FlashPoint(semilla)
            while not m.is_terminado():
                inicial = m.to_dict()
                mensaje = m.step()
                json.dumps(mensaje, allow_nan=False)
                reconstruido = aplicar_eventos(inicial, mensaje)
                final = mensaje["estadoFinal"]
                for clave in claves:
                    self.assertEqual(reconstruido[clave], final[clave], (semilla, m.turno, clave))
                for a, b in zip(reconstruido["agentes"], final["agentes"]):
                    for campo in ("x", "y", "actionPoints", "apGuardados", "cargandoVictima"):
                        self.assertEqual(a[campo], b[campo], (semilla, m.turno, a["id"], campo))
                cargadas = sum(a.victima_id is not None for a in m.agentes)
                self.assertEqual(m.bolsa_pois["victima"] + int(np.count_nonzero(m.pois == 2)) +
                                 cargadas + m.victimas_rescatadas + m.victimas_perdidas, 12)
                asignadas = [t["agente"] for t in m.cortana.tareas if t["estado"] == "asignada"]
                self.assertEqual(len(asignadas), len(set(asignadas)))
                for a in m.agentes:
                    self.assertTrue(0 <= a.ap <= 6 and 0 <= a.ap_guardados <= 2)
                    if m.mapa.es_interior(a.posicion):
                        self.assertNotEqual(m.fuego[a.posicion], FUEGO)
                for e in mensaje["eventos"]:
                    if e.get("costoAP", 0):
                        self.assertEqual(e["agenteId"], mensaje["agenteId"])

    def test_referencia_notebook_hasta_primer_golpe(self):
        """Iguala el costo total de derribo; compara antes de introducir daño por etapas."""
        notebook = Path(__file__).resolve().parents[1] / "agente_simulacion.ipynb"
        nb = json.loads(notebook.read_text(encoding="utf-8"))
        ns = {"np": np, "random": random.Random(), "heapq": heapq, "deepcopy": deepcopy}
        ids = {"combinacion-mapa", "combinacion-config", "combinacion-funciones",
               "agentes-cortana", "agentes-logica", "combinacion-simulacion"}
        with contextlib.redirect_stdout(io.StringIO()):
            for celda in nb["cells"]:
                if celda.get("id") in ids:
                    exec("".join(celda["source"]), ns)
        # La decisión de ruta ya cambia antes del primer golpe: comparar ambos
        # planificadores con el mismo costo total de 4 AP evita esa diferencia esperada.
        ns["COSTOS"]["derribar"] = 4
        comparados = 0
        for semilla in range(42, 52):
            m = FlashPoint(semilla)
            ns["reiniciar_simulacion"](semilla, guardar_historial=False)
            for nombre, viejo in (("verticales", "paredes_verticales"), ("horizontales", "paredes_horizontales")):
                esperado = np.where(ns[viejo] == 4, ENTRADA, ns[viejo])
                np.testing.assert_array_equal(getattr(m.mapa, nombre), esperado)
            for turno in range(1, 7):
                mensaje = m.step()
                if m.mapa.dano_estructura:
                    break  # Daño de paredes es precisamente la regla que ahora cambia.
                ns["turno_actual"] = turno
                ns["agentes"][(turno - 1) % 6].step()
                args = (ns["matrixFuego"], ns["matrixPois"], ns["matrixPoisRevelado"])
                _, _, perdidas = ns["advance_fire"](*args)
                ns["gameMasterCortana"]()
                perdidas += ns["flashover"](*args)
                ns["gameMasterCortana"]()
                perdidas += ns["resolver_agentes_en_fuego"]()
                ns["victimas_perdidas"] += sum(e[0] == "victima_perdida" for e in perdidas)
                ns["replenish_poi"](*args, ns["bolsa_pois"])
                ns["gameMasterCortana"]()
                for actual, esperado in ((m.fuego, ns["matrixFuego"]), (m.pois, ns["matrixPois"]),
                                          (m.pois_revelado, ns["matrixPoisRevelado"])):
                    np.testing.assert_array_equal(actual, esperado, err_msg=f"semilla={semilla}, turno={turno}")
                self.assertEqual(m.bolsa_pois, ns["bolsa_pois"])
                for a, b in zip(m.agentes, ns["agentes"]):
                    self.assertEqual((a.posicion, a.ap, a.ap_guardados), (b.posicion, b.ap, b.ap_guardados))
                comparados += 1
        self.assertGreaterEqual(comparados, 10)


if __name__ == "__main__":
    unittest.main()
