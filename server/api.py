"""Una partida por servidor; Unity solicita el siguiente turno al terminar de animar."""

from threading import RLock

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from models_edve import FlashPoint
from models_edve.config import Reglas


def create_app():
    app = Flask(__name__)
    app.extensions["flashpoint_game"] = FlashPoint()
    lock = RLock()

    def leer_json(campos):
        datos = request.get_json() if request.get_data() else {}
        if not isinstance(datos, dict):
            raise ValueError("El cuerpo debe ser un objeto JSON.")
        desconocidos = set(datos) - set(campos)
        if desconocidos:
            raise ValueError("Campos no reconocidos: " + ", ".join(sorted(desconocidos)))
        return datos

    @app.errorhandler(ValueError)
    @app.errorhandler(BadRequest)
    @app.errorhandler(UnsupportedMediaType)
    def error_peticion(error):
        return jsonify({"error": str(error)}), 400

    @app.get("/game/state")
    def get_state():
        with lock:
            return jsonify(app.extensions["flashpoint_game"].to_dict())

    @app.post("/game/step")
    def step():
        datos = leer_json({"ahorrar"})
        with lock:
            return jsonify(app.extensions["flashpoint_game"].step(ahorrar=datos.get("ahorrar", False)))

    @app.post("/game/new")
    def new_game():
        datos = leer_json({"semilla", "maxTurnos", "danoParaColapso"})
        reglas = Reglas(max_turnos=datos.get("maxTurnos", 300),
                        dano_para_colapso=datos.get("danoParaColapso", 24))
        nueva = FlashPoint(semilla=datos.get("semilla", 42), reglas=reglas)
        with lock:
            app.extensions["flashpoint_game"] = nueva
            return jsonify(nueva.to_dict())

    return app


app = create_app()
