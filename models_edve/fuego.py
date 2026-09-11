"""Una tirada tras cada Spartan; explosiones rectas y flashover a través de pasos libres."""

from .config import COLUMNAS, DIRECCIONES, FILAS, FUEGO, HUMO, PARED, PARED_DANADA, VACIO
from .pois import perder_poi


def explosion(model, origen):
    pasos, incendiadas = [], []
    for dr, dc in DIRECCIONES:
        actual = origen
        while not model.hay_colapso():
            destino = (actual[0] + dr, actual[1] + dc)
            estado = model.mapa.estado_entre(actual, destino)
            if estado in (PARED, PARED_DANADA):
                pasos.append(model.mapa.danar_pared(actual, destino))
                # Incluso el segundo impacto termina aquí. El hueco queda libre
                # para posteriores explosiones, movimiento y flashover.
                break
            if not model.mapa.puede_pasar(actual, destino):
                # Puerta cerrada o exterior: no se crea fuego fuera del tablero.
                break
            model.fuego[destino] = FUEGO
            pasos.append({"esPared": False, "row": destino[0], "col": destino[1], "estadoNuevo": FUEGO})
            incendiadas.append(destino)
            actual = destino
    model.emitir("explosion", row=origen[0], col=origen[1], pasos=pasos)
    # Las consecuencias se registran después del evento que las provoca.
    for posicion in incendiadas:
        perder_poi(model, posicion)


def flashover(model):
    cambio = True
    while cambio:
        cambio = False
        for r in range(FILAS):
            for c in range(COLUMNAS):
                if model.fuego[r, c] != HUMO:
                    continue
                for dr, dc in DIRECCIONES:
                    vecino = (r + dr, c + dc)
                    if (model.mapa.es_interior(vecino) and model.fuego[vecino] == FUEGO
                            and model.mapa.puede_pasar((r, c), vecino)):
                        model.fuego[r, c] = FUEGO
                        model.emitir("fuego_aparece", row=r, col=c, estadoNuevo=FUEGO, causa="flashover")
                        perder_poi(model, (r, c))
                        cambio = True
                        break


def avanzar_fuego(model):
    r, c = model.random.randint(0, FILAS - 1), model.random.randint(0, COLUMNAS - 1)
    model.tiradas_fuego += 1
    model.emitir("tirar_dados", dado1=r + 1, dado2=c + 1, proposito="fuego")
    if model.fuego[r, c] == VACIO:
        model.fuego[r, c] = HUMO
        model.emitir("humo_cae", row=r, col=c, estadoNuevo=HUMO)
    elif model.fuego[r, c] == HUMO:
        model.fuego[r, c] = FUEGO
        model.emitir("fuego_aparece", row=r, col=c, estadoNuevo=FUEGO, causa="humo_sobre_humo")
        perder_poi(model, (r, c))
    else:
        explosion(model, (r, c))

