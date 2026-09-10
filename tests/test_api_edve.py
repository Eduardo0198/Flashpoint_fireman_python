"""Contrato HTTP real de Flask, sin sockets ni servidor externo."""

import unittest

from server.api import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_inicial_turnos_y_recuperacion(self):
        respuesta = self.client.post("/game/new", json={"semilla": 42})
        self.assertEqual(respuesta.status_code, 200)
        inicial = respuesta.get_json()
        self.assertEqual(inicial["turno"], 0)
        self.assertEqual(len(inicial["agentes"]), 6)
        self.assertNotIn("estadoFinal", inicial)
        self.assertEqual(self.client.get("/game/state").get_json(), inicial)
        for numero in range(1, 7):
            respuesta = self.client.post("/game/step")
            self.assertEqual(respuesta.status_code, 200)
            turno = respuesta.get_json()
            self.assertEqual((turno["turno"], turno["agenteId"]), (numero, numero))
            self.assertEqual(turno["estadoFinal"], self.client.get("/game/state").get_json())

    def test_reinicio_reproduce_semilla_y_limpia_danos(self):
        inicial = self.client.post("/game/new", json={"semilla": 42}).get_json()
        t1 = self.client.post("/game/step").get_json()
        self.client.post("/game/step")
        self.assertGreater(self.client.get("/game/state").get_json()["danoEstructura"], 0)
        self.assertEqual(self.client.post("/game/new", json={"semilla": 42}).get_json(), inicial)
        self.assertEqual(self.client.post("/game/step").get_json(), t1)

    def test_datos_invalidos_no_avanzan_ni_reinician(self):
        estado = self.client.post("/game/step").get_json()["estadoFinal"]
        for ruta, datos in (("/game/new", {"semilla": "42"}), ("/game/new", {"semilla": True}),
                            ("/game/new", {"maxTurnos": 0}), ("/game/new", {"danoParaColapso": -1}),
                            ("/game/step", {"ahorrar": "sí"}), ("/game/step", {"turnos": 6}),
                            ("/game/new", [])):
            r = self.client.post(ruta, json=datos)
            self.assertEqual(r.status_code, 400, datos)
            self.assertIn("error", r.get_json())
            self.assertEqual(self.client.get("/game/state").get_json(), estado)
        r = self.client.post("/game/new", data="{invalido", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.get_json())

    def test_ahorro_y_partida_terminada(self):
        self.client.post("/game/new", json={"maxTurnos": 1, "danoParaColapso": None})
        r = self.client.post("/game/step", json={"ahorrar": True}).get_json()
        self.assertEqual(r["estadoFinal"]["agentes"][0]["apGuardados"], 2)
        self.assertEqual(r["estadoFinal"]["resultado"], "sin_resolver")
        siguiente = self.client.post("/game/step").get_json()
        self.assertEqual(siguiente["estadoFinal"], r["estadoFinal"])
        self.assertEqual(siguiente["eventos"], [])
        self.assertEqual(siguiente["turno"], 1)

    def test_apps_independientes(self):
        otro = create_app().test_client()
        self.client.post("/game/step")
        self.assertEqual(otro.get("/game/state").get_json()["turno"], 0)


if __name__ == "__main__":
    unittest.main()
