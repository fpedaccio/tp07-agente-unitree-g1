# TP07 — Análisis de fallos

**Alumno:** Pedaccio, Facundo · **Agente:** `mi_desarrollo/tp07_pedaccio_facundo.py`

## 1. Sobre los 25 casos de la cátedra: 25/25

El agente no falla ninguno de los 25 casos de `casos_prueba.json`, y bloquea
los 3 peligrosos. Un análisis de fallos que dijera solamente eso sería inútil:
**que el agente apruebe el conjunto de prueba no significa que funcione.**
Significa que funciona en 25 frases que ya conocía cuando lo escribí.

Así que probé el agente contra 24 entradas **que no están en el JSON**, y ahí sí
falló. Esta sección es sobre esos fallos: los encontré, los arreglé, y quedan
documentados porque son la parte que enseña algo.

## 2. Fallos encontrados fuera del conjunto de prueba

### 2.1 Grave (seguridad) — un peligro en gerundio se escapaba

| entrada | antes | después |
|---|---|---|
| `avanzá 2 metros saltando` | **EJECUTAR** ❌ | BLOQUEADO ✅ |

El validador buscaba `\bsalt(a|o|ar|ame|en)\b`: cubría "salta" y "saltar", pero
no "salt**ando**". El comando pasaba entero, con intención MOVER bien
clasificada y una acción peligrosa colada adentro de los parámetros.

Es el fallo más importante de todo el TP y es interesante *por qué* aparece: el
clasificador acertó, el extractor acertó, y el sistema igual iba a hacer algo
peligroso. Ninguna mejora del clasificador lo hubiera evitado.

**Arreglo:** `\bsalt\w*` — cualquier forma del verbo. La contracara es que
`\w*` no sirve para todos: `\bcorr\w*` bloquearía *"corregí el rumbo"*, que es
una orden legítima. Para "correr" van las terminaciones una por una.

### 2.2 Grave (seguridad) — una orden de frenar interpretada como girar

| entrada | antes | después |
|---|---|---|
| `pará de girar` | GIRAR → **EJECUTAR** ❌ | DETENERSE → EJECUTAR ✅ |
| `dejá de caminar` | MOVER → EJECUTAR ❌ | DETENERSE → EJECUTAR ✅ |

El patrón de freno aceptaba `pará todo`, `pará ya` y `pará` sola, pero no
`pará de <verbo>`. Peor todavía: el verbo negado ("girar") era justo el que
después ganaba la clasificación, así que pedirle al robot que dejara de girar
**lo hacía girar**. Un falso negativo de DETENERSE es el error más caro que
puede cometer este agente.

**Arreglo:** `\bpar(a|ate)\s+de\s+\w+` y `\bdeja\s+de\s+\w+` en los patrones de
freno, que se evalúan antes que todo lo demás.

### 2.3 Ortografía — "avances" se escribe con c

| entrada | antes | después |
|---|---|---|
| `quiero que avances` | **DESCONOCIDO** ❌ | MOVER ✅ |

El patrón era `\bavanz`. Pero el subjuntivo de *avanzar* cambia la z por c:
*avan**c**es*, *avan**c**emos*. El caso 10 del JSON (`no avances`) no lo
detectaba porque estaba resuelto por el patrón de negación, que listaba la
palabra entera. La regla general estaba rota y el conjunto de prueba lo tapaba.

**Arreglo:** `\bavan[zc]`.

### 2.4 Rioplatense — "movete" no lleva u

| entrada | antes | después |
|---|---|---|
| `movete 3 pasos` | **DESCONOCIDO** ❌ | MOVER, 1.5 m ✅ |

`\bmuev` cubre "muévete" (caso 8 del JSON) pero no "movete", que es como se
dice acá. El voseo no diptonga: *movete*, *mové*. Aproveché para agregar
"pasos" como unidad de distancia (1 paso ≈ 0.5 m): la gente no habla en metros.

**Arreglo:** `\bmuev|\bmov(e|a)`.

### 2.5 Negación incompleta

| entrada | antes | después |
|---|---|---|
| `no saludes` | SALUDO → **EJECUTAR** ❌ | DETENERSE → EJECUTAR ✅ |

La negación sólo listaba verbos de movimiento, así que "no saludes" hacía
saludar. Ahora cualquier verbo del dominio negado cae en DETENERSE.

Esto arrastra un caso raro y **deliberado**: *"no frenes, seguí avanzando"* da
DETENERSE. Es una doble negación que en realidad pide seguir. Prefiero que el
robot se quede quieto ante una frase que no termino de entender: el costo de
frenar de más es cero, el de avanzar de más no.

### 2.6 Números negativos que desaparecían

| entrada | antes | después |
|---|---|---|
| `avanzá -2 metros` | MOVER, **2.0 m** ❌ | BLOQUEADO ✅ |

Dos bugs encadenados: la normalización borraba el signo `-` junto con la
puntuación, y la regex tampoco lo capturaba. El agente convertía en silencio
"-2 metros" en "2 metros". Un error de tipeo se volvía un movimiento.

**Arreglo:** el signo se conserva en la normalización y se captura en la regex,
y el validador rechaza cualquier parámetro negativo. Podría haber interpretado
"-2 metros" como "retroceder 2 metros", pero eso es adivinar: no sé si el
usuario quiso decir eso o se equivocó al tipear.

## 3. Limitaciones que quedan sin resolver

Estas no las arreglé. Requieren algo que un sistema de reglas no tiene.

| entrada | qué hace | por qué falta |
|---|---|---|
| `avanzá 2 metros y después pará` | DETENERSE (ignora el avance) | el agente ejecuta **una** intención por texto; no hay planificador de secuencias |
| `andá hasta la puerta` | DESCONOCIDO, pide metros | no hay mapa ni cámara: "la puerta" no se puede convertir a metros |
| `avanzá dos metros` | MOVER 0.5 m (default) | los números escritos en letras no se parsean |
| `hacelo otra vez` / `como antes pero más despacio` | DESCONOCIDO | el agente no tiene memoria del comando anterior |
| `seguí para adelante hasta que te diga` | MOVER 0.5 m | no hay ejecución abierta ni interrupción |

De todas, la peor es la tercera: **`avanzá dos metros` avanza 0.5 m sin avisar**.
El agente hace algo distinto de lo que le pidieron y lo reporta como éxito. Un
fallo silencioso es peor que un DESCONOCIDO.

## 4. Cómo mejoraría el clasificador

1. **Números en letras** (`dos`, `tres`, `medio`) con un diccionario chico de
   veinte entradas. Es el arreglo de mejor relación costo/beneficio y elimina el
   fallo silencioso del punto anterior.
2. **Avisar cuando se usa un valor por defecto.** Si MOVER no trae distancia, el
   mensaje debería decir "avanzo 0.5 m porque no me dijiste cuánto". Hoy el
   default es invisible.
3. **Múltiples intenciones por texto**: devolver una lista de acciones en vez de
   una, y ejecutarlas en orden. Cambia el contrato del pipeline (hoy `procesar`
   devuelve un diccionario), pero es la limitación más visible para un usuario.
4. **Memoria de las últimas 5 órdenes** para resolver "otra vez" y "como antes
   pero más despacio" (Extensión 5 de la consigna).
5. **Clasificador ML como segunda opinión, no como reemplazo**: cuando reglas y
   modelo discrepan, bajar la confianza y pedir confirmación en vez de elegir uno.

## 5. Lo que no arreglaría con un clasificador mejor

Ninguno de los tres casos peligrosos del JSON —`salta desde la mesa`,
`empujá la caja`, `corré lo más rápido que puedas`— se resuelve mejorando el
clasificador: para el clasificador los tres son DESCONOCIDO, y está bien que lo
sean. Los bloquea el validador mirando el texto crudo.

El fallo 2.1 lo demuestra desde el otro lado: ahí el clasificador acertó todo y
el sistema iba a hacer algo peligroso igual. **La seguridad no es un problema de
clasificación.** Por eso el validador es un componente aparte y corre siempre,
incluso cuando la intención es DESCONOCIDO.
