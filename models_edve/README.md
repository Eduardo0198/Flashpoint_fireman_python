# Simulación para Unity

Este paquete extrae la lógica de `agente_simulacion.ipynb` a módulos que se pueden
importar sin Jupyter ni Matplotlib. Incorpora daño de paredes y los dos formatos
JSON acordados. Cada `FlashPoint` tiene su propio mapa, agentes, tareas, bolsa y
generador aleatorio. El notebook conserva la simulación anterior como referencia;
la API ejecuta esta nueva versión.

## Archivos

| Archivo | Responsabilidad |
| --- | --- |
| `config.py` | Costos, prioridades, entradas, POIs y límites configurables. |
| `mapa.py` | Mapa de la imagen, puertas, entradas y daño de cada segmento. |
| `agente.py` | A*, utilidad, acciones, ahorro, transporte y retirada. |
| `cortana.py` | `gameMasterCortana`, cambios y reserva exclusiva de tareas. |
| `fuego.py` | Tirada individual, explosiones y flashover. |
| `pois.py` | Bolsa finita, reposición y pérdidas por fuego. |
| `flashpoint_model.py` | Estado de una partida, orden de turnos y resultado. |
| `protocolo_unity.py` | Traducción al JSON inicial y al JSON de cada turno. |
| `exportar.py` | Ejemplos reproducibles para probar el lector de Unity. |
| `../server/api.py` | HTTP, conectado al modelo nuevo. |

## Ejecutar y conectar

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements_edve.txt
.venv\Scripts\python.exe main.py
```

El servidor escucha en el puerto 5000. En Unity, usar `http://localhost:5000` si
corre en la misma computadora, o la IP de la computadora que ejecuta Python.
Hay una partida compartida por proceso; `/game/new` la reemplaza para todos sus
clientes. Ejecutar un único proceso del servidor para esta integración.

| Petición | Respuesta |
| --- | --- |
| `POST /game/new` | JSON inicial, turno 0, mapa completo y seis Spartans afuera. |
| `POST /game/step` | `{ "turno": 1, "agenteId": 1, "eventos": [...], "estadoFinal": {...} }`. |
| `GET /game/state` | Mismo formato completo del inicial, en el turno actual, sin avanzar. |

Los cuerpos son opcionales. `/game/new` acepta
`{"semilla":42,"maxTurnos":300,"danoParaColapso":24}`. La misma semilla reproduce
la partida; usar otra para obtener una diferente. `danoParaColapso: null` permite
comparar partidas sin derrota por colapso. `/game/step` acepta `{"ahorrar":true}`
para que el agente activo guarde AP en ese turno. Los datos inválidos devuelven
HTTP 400 y un objeto `error`, sin modificar la partida.

Unity debe crear la escena con el primer estado y solicitar un turno a la vez.
Animar los eventos en su orden y aplicar `estadoFinal` al terminar para que las
capas y posiciones coincidan con Python. Después solicitar el siguiente turno.
Los eventos de retirada pertenecen a la misma fase de fuego que los causa:
resolverlos en esa fase, sin esperar al próximo turno del agente afectado.
Si una respuesta de `/game/step` se pierde, consultar `/game/state` antes de
solicitar otro paso; repetir `/game/step` durante una partida avanza de nuevo.
Al terminar, las siguientes peticiones devuelven el mismo turno y `eventos: []`.

No se incluyen scripts C# del proyecto Unity en este repositorio. El lector
existente debe incorporar los eventos adicionales descritos abajo; los ejemplos
permiten probarlo sin ejecutar una partida en vivo.

## Coordenadas y estados

Todas las coordenadas son de base cero. En agentes, `x = columna`, `y = fila`.
En eventos, `row = fila`, `col = columna`. Los dados sí empiezan en uno:
`dado1 = row + 1`, `dado2 = col + 1`. `proposito` distingue fuego y reposición de POI;
una reposición puede repetir tiradas si el destino ya tiene un POI.

| Campo del estado | Tamaño | Índice / valores |
| --- | --- | --- |
| `tablero` | 48 | `row * 8 + col`; 0 vacío, 1 humo, 2 fuego. |
| `pois` | 48 | `row * 8 + col`; 0 ninguno, 1 falsa alarma, 2 víctima. |
| `poisRevelado` | 48 | Booleanos; ocultar el tipo de POI mientras sea `false`. |
| `paredesVerticales` | 54 | `row * 9 + col`; 6 filas por 9 límites. |
| `paredesHorizontales` | 56 | `row * 8 + col`; 7 límites por 8 columnas. |

Los dos arreglos de bordes usan exactamente estos valores:

| Valor | Significado para Unity |
| --- | --- |
| 0 | Paso abierto, incluida una entrada o una pared destruida. |
| 1 | Pared intacta. |
| 2 | Puerta cerrada. |
| 3 | Puerta abierta. |
| 4 | Pared dañada: todavía bloquea agentes y fuego. |

Internamente `ENTRADA = 5`; `protocolo_unity.py` la convierte a `0`. El código de
entrada del notebook anterior no se envía como pared dañada. `entradas` añade
nombre, borde y coordenadas interior/exterior para identificar los cuatro accesos:

| Entrada | Exterior `(x,y)` | Interior `(x,y)` |
| --- | --- | --- |
| arriba | `(5,-1)` | `(5,0)` |
| izquierda | `(-1,2)` | `(0,2)` |
| derecha | `(8,3)` | `(7,3)` |
| abajo | `(2,6)` | `(2,5)` |

Los agentes iniciales son S1/S5 a la izquierda, S2/S6 a la derecha, S3 abajo y S4
arriba. Pueden compartir una celda. El exterior no añade filas a los arreglos de
fuego y POIs; el movimiento exterior se limita a estos cuatro accesos.

Cada agente conserva `id`, `x`, `y`, `actionPoints` y añade `nombre`, `apGuardados`,
`cargandoVictima`, `entrada` y `tareaId` (0 si no tiene tarea). `actionPoints` es
el saldo activo: empieza en 0, recibe 4 más lo ahorrado al iniciar su turno y vuelve
a 0 al guardar el sobrante. `apGuardados` conserva hasta 2 para la siguiente vez.
Así se evita contar dos veces los puntos. Los eventos de acciones incluyen el
saldo inmediatamente después de ejecutarse.

El estado también incluye `victimasRescatadas`, `victimasPerdidas`,
`danoEstructura`, `terminado`, `resultado`, `siguienteAgenteId` (0 al finalizar),
`semilla` y `versionProtocolo: 1`. `resultado` es `null`, `victoria`,
`derrota_victimas`, `derrota_colapso` o `sin_resolver`. `tareaId` es información
de diagnóstico del estado final; las reservas canceladas por cambios en el mapa
se consultan en Cortana.

## Reglas de esta versión

- Seis agentes, en orden S1–S6. Cada turno es las acciones de uno, una tirada de
  fuego, flashover, retirada de afectados, evaluación de derrota y reposición.
- 4 AP nuevos y hasta 2 ahorrados. Mover cuesta 1, incluso llevando víctima;
  recogerla cuesta 2; entregarla afuera cuesta 0. Abrir o cerrar puerta cuesta 1.
- Apagar fuego completo cuesta 2; humo, 1; revelar POI, 0. Se apaga desde una
  vecina ortogonal con paso libre; el humo también desde la misma casilla.
- El humo es transitable. El fuego bloquea movimiento. Si alcanza a un agente,
  este vuelve al exterior de su entrada original y pierde la víctima que llevaba,
  contada una sola vez. Conserva sus AP ahorrados.
- Cortana reserva tareas sin duplicarlas y permite continuarlas en turnos
  posteriores. Prioridades: fuego 10, víctima 6, POI 6, humo 2. Utilidad:
  `prioridad / (costo de ruta A* + 1)`. La ruta incluye preparar puertas y paredes;
  la acción de apagar/recoger se paga aparte.
- Hay 18 POIs totales: 12 víctimas y 6 falsas alarmas. Los tres iniciales salen de
  esa misma bolsa. Reponer hasta tres en el mapa, mientras queden en la bolsa;
  un POI nuevo limpia humo o fuego de su casilla.
- Humo sobre vacío crea humo; sobre humo crea fuego; sobre fuego causa explosión.
  La explosión recorre las cuatro direcciones en línea recta hasta un bloqueo.
  Puertas cerradas bloquean sin dañarse; entradas abiertas permiten salir del
  edificio al frente de explosión, sin crear fuego en coordenadas exteriores.
- Cada hachazo cuesta **2 AP y añade una marca**. La primera daña la pared; la
  segunda la destruye. Derribar una intacta cuesta **4 AP**, y después mover
  cuesta otro AP. Puede repartirse entre turnos o entre agentes.
- Cada impacto de explosión añade una marca a la pared alcanzada, sin consumir
  AP. Ese frente se detiene incluso cuando el impacto destruye la pared; el paso
  queda disponible para movimiento, flashover y explosiones posteriores.
- Las marcas de hachazos y explosiones se acumulan en `danoEstructura`, incluso
  después de destruir la pared. Con 24 se pierde por colapso. Ese límite procede
  del modelo anterior del repositorio y se puede configurar con `Reglas` o la API.
- Se gana rescatando 7, se pierde al perder 4 víctimas o por colapso. Un rescate
  ganador o un hachazo que provoca colapso termina la partida antes de tirar fuego.
  El límite de 300 turnos individuales produce `sin_resolver` si no hubo desenlace.
- Abrir puertas es parte de la navegación automática. Cerrar está disponible en
  `Bombero.cerrar_puerta(vecino)` por 1 AP; no se añadió una nueva prioridad autónoma
  para decidir cuándo cerrarlas.

## Eventos que debe leer Unity

Todos conservan `tipo`. Los eventos de agentes incluyen `agenteId`, `costoAP`,
`actionPoints`, `apGuardados`, `cargandoVictima` y `tareaId`. `row/col` indican el
destino de la acción: solo `agente_mueve` y `agente_retirada` cambian la posición
del agente. En eventos de puerta o pared indican **el borde**, no la casilla.

| Tipo | Efecto y campos específicos |
| --- | --- |
| `agente_inicia_turno` | Actualizar AP activos y ahorrados. |
| `agente_ahorra_ap` | Activos a 0; guardar `apGuardados`; `descartados` indica sobrante. |
| `agente_asigna_tarea` / `agente_libera_tarea` | Información de coordinación; no modifica capas visuales. |
| `agente_mueve` | Mover a `row/col`; también incluye `origenRow/origenCol`. |
| `agente_apaga_fuego` / `agente_apaga_humo` | Limpiar la casilla objetivo; `estadoNuevo: 0`. |
| `agente_abre_puerta` / `agente_cierra_puerta` | Actualizar borde por `row/col/esVertical/estadoNuevo`. |
| `agente_dana_pared` / `agente_derriba_pared` | Actualizar borde a 4 o 0 y `danoEstructura`. |
| `agente_revela_poi` | Mostrar `tipoPoi`; retirar si `retirado: true`; marcar revelado. |
| `agente_recoge_victima` | Borrar POI y su marca de revelado; mostrar víctima cargada. |
| `victima_rescatada` | Quitar víctima cargada y actualizar `victimasRescatadas`. |
| `tirar_dados` | Animar `dado1/dado2`; `proposito` vale `fuego` o `poi`. |
| `humo_cae` | Casilla a humo (`estadoNuevo: 1`). |
| `fuego_aparece` | Casilla a fuego (`estadoNuevo: 2`), causa humo acumulado o flashover. |
| `explosion` | Aplicar `pasos` en orden, diferenciando celdas de bordes por `esPared`. |
| `poi_cae` | Colocar `tipoPoi` oculto; si `apagaFuego`, limpiar humo/fuego. |
| `victima_perdida` | Actualizar contador. Si `enBrazos`, quitar carga del `agenteId`; si no, borrar POI de `row/col` y marcarlo revelado. |
| `falsa_alarma_quemada` | Borrar POI de `row/col`, marcar revelado, sin sumar víctima perdida. |
| `agente_retirada` | Mover al exterior `row/col`; incluye origen, entrada y `victimaPerdida`. |
| `partida_terminada` | Mostrar `resultado` y contadores finales. |

`explosion.pasos` tiene el formato acordado:

```json
{
  "tipo": "explosion",
  "row": 2,
  "col": 3,
  "pasos": [
    {"esPared": false, "row": 2, "col": 4, "estadoNuevo": 2},
    {"esPared": true, "row": 2, "col": 5, "esVertical": true, "estadoNuevo": 4, "danoEstructura": 1}
  ]
}
```

El ejemplo anterior ilustra campos; para reproducir el mapa real usar los archivos
generados en `ejemplos/`. Si una falsa alarma ya fue retirada, el valor de
`poisRevelado` en una casilla con `pois: 0` no dibuja ningún objeto.

## Validar y generar ejemplos

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m models_edve.exportar --semilla 42 --turnos 6
```

`ejemplos/inicial.json` y `ejemplos/turno_001.json` a `turno_006.json` son mensajes
consecutivos generados por el motor. El segundo turno ya incluye daño por explosión.
Para exportar una partida más larga, usar una carpeta nueva y `--turnos 300`;
el exportador se detiene al terminar la partida. No elimina archivos anteriores.

Para comparar 50 partidas desde Python:

```python
from models_edve.flashpoint_model import simular_partidas

resultados, resumen = simular_partidas(50, semilla_base=42)
print(resumen)
```

Las pruebas contrastan el mapa y los turnos previos al primer golpe con el notebook,
igualando en memoria el costo total de derribo. Comprueban reglas de AP, daño,
explosiones, retirada, reservas y conservación de víctimas. Un cliente de prueba
reconstruye el estado visual solo con eventos y lo compara con `estadoFinal` durante
partidas completas. Las pruebas HTTP usan el cliente real de Flask.

Verificación realizada: **27 pruebas aprobadas**. En 50 partidas con seis agentes,
semillas 42–91, máximo 300 turnos y colapso en 24 marcas: **3 victorias, 3 derrotas
por víctimas y 44 por colapso**, sin partidas inconclusas; promedio de 35.06 turnos.
Las semillas ganadoras fueron 46, 67 y 91. La semilla 42 terminó por colapso en el
turno 47, con 4 rescatadas y 2 perdidas. Estos resultados corresponden a las nuevas
reglas de daño, no a la versión anterior del notebook.

## Checklist de integración

- [x] Separar mapa, agentes, Cortana, fuego y POIs del notebook.
- [x] Incorporar daño en dos marcas, rutas con costo actualizado y colapso configurable.
- [x] Traducir entradas y paredes al convenio de Unity, conservando coordenadas exteriores.
- [x] Producir estado inicial, eventos ordenados y estado final por turno individual.
- [x] Conectar los endpoints existentes al motor nuevo.
- [x] Añadir pruebas de reglas y reconstrucción de mensajes.
- [ ] Validar las animaciones en el proyecto Unity del compañero.
