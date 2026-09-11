"""Exporta mensajes reales y consecutivos sin levantar Flask ni abrir el notebook."""

import argparse
import json
from pathlib import Path

from .flashpoint_model import FlashPoint


def exportar(salida, semilla=42, turnos=6):
    if type(turnos) is not int or turnos < 0:
        raise ValueError("turnos debe ser un entero no negativo.")
    carpeta = Path(salida)
    carpeta.mkdir(parents=True, exist_ok=True)
    model = FlashPoint(semilla=semilla)
    mensajes = [("inicial.json", model.to_dict())]
    for _ in range(turnos):
        if model.is_terminado():
            break
        mensajes.append((f"turno_{model.turno + 1:03d}.json", model.step()))
    for nombre, mensaje in mensajes:
        (carpeta / nombre).write_text(json.dumps(mensaje, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                      encoding="utf-8")
    return len(mensajes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("models_edve/ejemplos"))
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--turnos", type=int, default=6)
    args = parser.parse_args()
    print(f"Exportados {exportar(args.salida, args.semilla, args.turnos)} mensajes en {args.salida}")


if __name__ == "__main__":
    main()
