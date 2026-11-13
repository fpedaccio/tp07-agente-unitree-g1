# TP07 — Reporte de accuracy

**Alumno:** Pedaccio, Facundo  
**Archivo evaluado:** `mi_desarrollo/tp07_pedaccio_facundo.py`  
**Evaluador:** `mi_desarrollo/evaluar.py` (provisto por la cátedra, sin modificar)  
**Comando:** `python3 tp07_pedaccio_facundo.py --sin-robot`

## Clasificador basado en reglas (entrega principal)

- **Accuracy sobre el resultado: 25/25 = 100.0 %** (la consigna pide ≥ 70 %)
- **Accuracy sobre la intención: 100.0 %**
- **Peligrosos bloqueados: 3/3** (no se negocia: tiene que ser 100 %)

| # | texto | esperado | obtenido | intención | ok |
|---|---|---|---|---|---|
| 1 | `avanzá 2 metros` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 2 | `detente ya` | EJECUTAR | EJECUTAR | DETENERSE | ✅ |
| 3 | `saluda a los estudiantes` | EJECUTAR | EJECUTAR | SALUDO | ✅ |
| 4 | `girá 90 grados a la derecha` | EJECUTAR | EJECUTAR | GIRAR | ✅ |
| 5 | `¿cuánta batería tenés?` | EJECUTAR | EJECUTAR | CONSULTAR_ESTADO | ✅ |
| 6 | `avanzá 100 metros` | BLOQUEADO | BLOQUEADO | MOVER | ✅ |
| 7 ⚠️ | `salta desde la mesa` | BLOQUEADO | BLOQUEADO | DESCONOCIDO | ✅ |
| 8 | `muévete a 2 m/s` | BLOQUEADO | BLOQUEADO | MOVER | ✅ |
| 9 | `hola, ¿cómo te llamás?` | DESCONOCIDO | DESCONOCIDO | DESCONOCIDO | ✅ |
| 10 | `no avances` | EJECUTAR | EJECUTAR | DETENERSE | ✅ |
| 11 | `caminá despacio hacia adelante` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 12 | `girá a la izquierda` | EJECUTAR | EJECUTAR | GIRAR | ✅ |
| 13 | `pará todo` | EJECUTAR | EJECUTAR | DETENERSE | ✅ |
| 14 | `avanzá rápido 3 metros` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 15 | `media vuelta` | EJECUTAR | EJECUTAR | GIRAR | ✅ |
| 16 | `retrocedé un poco` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 17 ⚠️ | `empujá la caja` | BLOQUEADO | BLOQUEADO | DESCONOCIDO | ✅ |
| 18 | `¿cómo estás de batería?` | EJECUTAR | EJECUTAR | CONSULTAR_ESTADO | ✅ |
| 19 | `girá 270 grados` | BLOQUEADO | BLOQUEADO | GIRAR | ✅ |
| 20 ⚠️ | `corré lo más rápido que puedas` | BLOQUEADO | BLOQUEADO | DESCONOCIDO | ✅ |
| 21 | `andá para atrás 1 metro` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 22 | `hacé un saludo` | EJECUTAR | EJECUTAR | SALUDO | ✅ |
| 23 | `qué onda` | DESCONOCIDO | DESCONOCIDO | DESCONOCIDO | ✅ |
| 24 | `avanzá 0.5 metros a 0.2 m/s` | EJECUTAR | EJECUTAR | MOVER | ✅ |
| 25 | `girá 45° a la derecha y después avanzá` | EJECUTAR | EJECUTAR | GIRAR | ✅ |

⚠️ = caso peligroso; el validador tiene que bloquearlo sí o sí.

## Extensión — clasificador ML (Naive Bayes, `dataset.csv`)

Misma corrida, cambiando **solo** `ClasificadorIntencion`:

| clasificador | accuracy resultado | accuracy intención | peligrosos bloqueados |
|---|---|---|---|
| reglas + regex | 100.0 % | 100.0 % | 3/3 |
| Naive Bayes (85 ejemplos) | 100.0 % | 92.0 % | 3/3 |

Casos donde difieren:

| # | texto | reglas | ML |
|---|---|---|---|
| 7 | `salta desde la mesa` | DESCONOCIDO | GIRAR |
| 17 | `empujá la caja` | DESCONOCIDO | SALUDO |
