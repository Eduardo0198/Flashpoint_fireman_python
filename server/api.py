from flask import Flask, jsonify
from models.flashpoint_model import FlashPoint
app = Flask(__name__)
#Sesiones de las partidas
game = FlashPoint()
@app.route ("/game/state", methods=["GET"])
def get_state():
    return jsonify(game.to_dict())

#Los pasos que va a dar el agente 
@app.route("/game/step", methods=["POST"])
def step():
    game.step()
    return jsonify(game.to_dict())

@app.route("/game/new", methods=["POST"])
def new_game():
    global game
    game = FlashPoint()
    return jsonify(game.to_dict())
