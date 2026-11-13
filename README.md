# TP07 — Agente inteligente para el robot Unitree G1

Agente que interpreta comandos en lenguaje natural (castellano rioplatense) y
los traduce en acciones del robot Unitree G1, **rechazando los que no son
seguros**.

Inteligencia Artificial — Carreras de Informática, UADE.
**Alumno:** Pedaccio, Facundo

```
ACCURACY: 25/25 = 100.0 %   APRUEBA (>= 70 %)
PELIGROSOS BLOQUEADOS: 3/3   BIEN
```

## El pipeline

```
texto → Clasificador → Extractor → Validador → Ejecutor → robot
        de intención    de params   de seguridad
          ¿QUÉ?         ¿CUÁNTO?     ¿SE PUEDE?    ¿CÓMO?
```

| Etapa | Entrada | Salida |
|---|---|---|
| `ClasificadorIntencion` | texto | `MOVER`, `GIRAR`, `DETENERSE`, `SALUDO`, `CONSULTAR_ESTADO` o `DESCONOCIDO` |
| `ExtractorParametros` | texto + tipo | `{distancia_m, angulo_deg, velocidad_ms, direccion}` |
| `ValidadorSeguridad` | **texto** + tipo + params | `(bool, motivo)` |
| `Ejecutor` *(de la cátedra)* | tipo + params | órdenes de velocidad y tiempo al SDK |

## El hallazgo

Entrenando el clasificador ML de la extensión, el Naive Bayes clasificó
`salta desde la mesa` como **GIRAR** y `empujá la caja` como **SALUDO**: los dos
comandos peligrosos del conjunto, leídos como acciones ejecutables.

Los dos terminaron **BLOQUEADOS igual**.

| clasificador | accuracy resultado | accuracy intención | peligrosos bloqueados |
|---|---|---|---|
| reglas + regex | 100 % | 100 % | 3/3 |
| Naive Bayes (85 ejemplos) | 100 % | 92 % | 3/3 |

Clasificador peor, seguridad idéntica — porque el validador es una etapa aparte
que mira el texto original y no depende de que el clasificador acierte. Esa fila
es la justificación empírica de toda la arquitectura, y está desarrollada en el
[informe técnico](INFORME_TECNICO.md).

## Qué hay acá

| Archivo | Qué es |
|---|---|
| [`mi_desarrollo/tp07_pedaccio_facundo.py`](mi_desarrollo/tp07_pedaccio_facundo.py) | el agente completo: clasificador, extractor, validador, integración |
| [`mi_desarrollo/dataset.csv`](mi_desarrollo/dataset.csv) | 85 ejemplos anotados para la extensión ML |
| [`mi_desarrollo/comparar_ml.py`](mi_desarrollo/comparar_ml.py) | comparación reglas vs. Naive Bayes |
| [`REPORTE_ACCURACY.md`](REPORTE_ACCURACY.md) | tabla de los 25 casos de prueba |
| [`ANALISIS_FALLOS.md`](ANALISIS_FALLOS.md) | 6 bugs encontrados fuera del conjunto de prueba, y qué falta |
| [`INFORME_TECNICO.md`](INFORME_TECNICO.md) | pipeline, enfoque elegido, independencia del validador |

## Cómo correrlo

Este repo tiene **solo mi trabajo**. El simulador, el evaluador, el ejecutor y
los casos de prueba son de la cátedra y viven en su propio repo:

```bash
git clone https://github.com/tsamaan/UadeRobotLab.git
cd UadeRobotLab/05LaboratoriosTPs/TP07_Inteligencia_Artificial
```

Copiá los tres archivos de `mi_desarrollo/` de este repo dentro del
`mi_desarrollo/` de ahí, y corré la evaluación de los 25 casos:

```bash
cd mi_desarrollo && python3 tp07_pedaccio_facundo.py --sin-robot
```

Con el simulador 3D abierto (`INICIAR_SIMULADOR`), sin el flag, se agrega un
modo interactivo para escribirle órdenes al robot.

La extensión ML necesita `pip install scikit-learn`; si no está, el agente avisa
y sigue funcionando con reglas:

```bash
python3 comparar_ml.py     # reglas vs. ML, regenera el reporte
```

## Notas de plataforma (macOS)

Dos cosas que me costaron y no están en el instructivo:

- **El simulador no abre la ventana 3D con `python`.** MuJoCo en macOS exige su
  propio lanzador: `mjpython -m sim --robot g1 --materia tp07`. Con `python`
  normal cae a modo consola sin decir bien por qué.
- **El gesto de saludo no se dibuja.** El protocolo manda `"saludo"` y la
  animación del brazo se dispara con `"saludando"`: el gesto se registra y no se
  ve. Es un bug del simulador, arreglable con una línea en `sim/mundo.py`.
