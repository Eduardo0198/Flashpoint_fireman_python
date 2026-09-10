# Flashpoint_fireman_python

La API usa la simulación modular de [`models_edve`](models_edve/README.md), basada
en `agente_simulacion.ipynb`, con seis Spartans y daño de paredes en dos golpes.
El notebook conserva la versión de referencia anterior a esta extracción.

Desde PowerShell, en la raíz del repositorio:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements_edve.txt
.venv\Scripts\python.exe main.py
```

Unity recibe un estado inicial en `POST /game/new` y un mensaje con
`eventos` + `estadoFinal` en cada `POST /game/step` (puerto 5000).
`GET /game/state` permite recuperar el estado sin avanzar.

El contrato completo, los eventos adicionales y las reglas están en
[`models_edve/README.md`](models_edve/README.md). Los mensajes de ejemplo se generan con:

```powershell
.venv\Scripts\python.exe -m models_edve.exportar --turnos 6
.venv\Scripts\python.exe -m unittest discover -s tests -v
```
