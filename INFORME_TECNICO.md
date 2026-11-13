# TP07 — Informe técnico

**Agente inteligente para interpretar comandos y decidir acciones del robot**
Universidad Argentina de la Empresa — Inteligencia Artificial
**Alumno:** Pedaccio, Facundo

---

## 1. El problema

El agente recibe una cadena en castellano rioplatense —*"avanzá 2 metros"*,
*"pará todo"*, *"salta desde la mesa"*— y decide qué hace el robot Unitree G1.
Es un agente en el sentido clásico: **percibe** el entorno por un sensor (la
interfaz de texto), **razona** sobre lo percibido y **actúa** sobre el mundo
físico a través de actuadores. Lo que distingue este caso del NLP habitual es
la última parte: una clasificación equivocada no produce una respuesta mala,
produce **un robot de 35 kg moviéndose en un aula con gente alrededor**.

## 2. Arquitectura del pipeline

```
texto → Clasificador → Extractor → Validador → Ejecutor → robot
        de intención    de params   de seguridad
          ¿QUÉ?         ¿CUÁNTO?     ¿SE PUEDE?    ¿CÓMO?
```

Cada etapa contesta **una** pregunta y no sabe nada de las otras:

| Etapa | Clase | Entrada | Salida |
|---|---|---|---|
| 1 | `ClasificadorIntencion` | texto | uno de 6 tipos + confianza + regla que disparó |
| 2 | `ExtractorParametros` | texto + tipo | `{distancia_m, angulo_deg, velocidad_ms, direccion}` |
| 3 | `ValidadorSeguridad` | **texto** + tipo + params | `(bool, motivo)` |
| 4 | `Ejecutor` (provisto) | tipo + params | órdenes de velocidad y tiempo al SDK |

Las tres primeras comparten una única función `normalizar()`: minúsculas, sin
tildes, sin puntuación. Sacar las tildes resuelve de una sola vez el problema
morfológico del castellano: *avanzá / avanza*, *girá / gira*, *pará / para*
pasan a ser la misma cadena, y cada intención necesita **un** patrón en lugar de
tres. Es una decisión chica con un efecto grande sobre el tamaño del código.

**Unidades:** las etapas 1–3 trabajan en metros y grados, que es como habla la
gente. La conversión a velocidad y tiempo —lo único que entiende el SDK— vive
enteramente en el `Ejecutor`, que además parte los movimientos largos en tramos
que no superan los 5 s por orden. Ese límite es del robot, no del lenguaje, y
por eso no contamina las etapas de arriba.

## 3. Enfoque elegido: reglas, con ML como extensión

Implementé el **Nivel 1** (reglas + `re`) como motor principal y el **Nivel 2**
(Naive Bayes sobre 85 ejemplos anotados) como extensión activable con `--ml`.
La justificación no es que las reglas anden mejor —abajo se ve que en accuracy
empatan— sino tres propiedades que importan cuando el sistema mueve hardware:

1. **Auditabilidad.** Cada decisión devuelve la regla que la produjo
   (`"\bavan[zc]... (pos 0)"`). Cuando el agente se equivoca, sé exactamente qué
   patrón falló y lo arreglo. Con el Naive Bayes, la explicación de por qué
   *"empujá la caja"* dio SALUDO es una matriz de conteos de n-gramas.
2. **Comportamiento definido fuera de la distribución.** Ante una frase que no
   se parece a nada, las reglas devuelven DESCONOCIDO —que es la respuesta
   correcta—. El modelo estadístico **siempre** devuelve una de las cinco clases
   accionables, porque no tiene forma de decir "esto no lo vi nunca".
3. **Cero dependencias.** Un agente que controla un robot no puede quedarse mudo
   porque falta un paquete. Si scikit-learn no está, el agente avisa y sigue con
   reglas: eso está implementado y probado.

El costo de las reglas es real y lo asumo: no generalizan. Cada forma verbal
nueva es una línea nueva de regex, y el análisis de fallos muestra cuatro que se
me escaparon (`avances`, `movete`, `saltando`, `pará de girar`).

### Comparación medida sobre los mismos 25 casos

| clasificador | accuracy del resultado | accuracy de la intención | peligrosos bloqueados |
|---|---|---|---|
| reglas + regex | **100 %** (25/25) | **100 %** (25/25) | **3/3** |
| Naive Bayes (85 ejemplos) | **100 %** (25/25) | **92 %** (23/25) | **3/3** |

Métricas del modelo sobre 22 ejemplos retenidos del dataset (que no vio al
entrenar): accuracy 68.2 %, precision 66.1 %, recall 69.7 %, F1 67.2 %.

**Los dos casos donde el modelo se equivoca son el hallazgo central de este TP:**

| # | texto | reglas | Naive Bayes | resultado final |
|---|---|---|---|---|
| 7 | `salta desde la mesa` | DESCONOCIDO | **GIRAR** | BLOQUEADO |
| 17 | `empujá la caja` | DESCONOCIDO | **SALUDO** | BLOQUEADO |

El modelo tomó los dos comandos peligrosos del conjunto y los clasificó como
acciones perfectamente ejecutables. Si el clasificador fuera el único
responsable de la seguridad, el robot habría girado y saludado. **El resultado
final igual fue BLOQUEADO en los dos casos**, porque el validador es una etapa
aparte que mira el texto original y no depende de que el clasificador acierte.

Esa fila —clasificador peor, seguridad idéntica— es la justificación empírica de
toda la arquitectura, y es exactamente lo que la sección siguiente sostiene.

## 4. Por qué el validador es un componente independiente

Podría estar adentro del clasificador: unas reglas más, al final del método. No
lo está, por cuatro razones que se sostienen solas.

**a) Un error de clasificación no debe ser un error de seguridad.** Todo
clasificador se equivoca. Si la seguridad viviera adentro del que se equivoca,
los dos errores serían el mismo error. Separándolos, una clasificación mala
sigue terminando en un comando bloqueado — que es literalmente lo que se midió
en la tabla de arriba.

**b) El validador mira el texto crudo, no la intención.** Es la parte que más se
confunde. `salta desde la mesa` **no tiene intención válida**: ningún
clasificador lo reconoce, y está bien que no lo reconozca. Si DESCONOCIDO
salteara la validación, el comando más peligroso del conjunto sería el único que
se escapa. Por eso el orden en `procesar()` es:

```python
tipo = clasificar(texto)              # puede ser DESCONOCIDO
params = extraer(texto, tipo)
ok, motivo = validar(texto, tipo, params)   # SIEMPRE, incluso si es DESCONOCIDO
if not ok:  return bloqueado
if tipo == "DESCONOCIDO": return no_entendido
ejecutar(...)
```

La validación va **antes** de la salida por DESCONOCIDO, no después. Un comando
que no se entiende no es un comando inofensivo.

**c) Un clasificador correcto puede producir una acción peligrosa.** El fallo
2.1 del análisis lo muestra: en `avanzá 2 metros saltando`, el clasificador
acierta (MOVER), el extractor acierta (2 m) y la acción es peligrosa igual. No
hay mejora del clasificador que lo evite, porque el peligro no está en la
intención sino en una palabra que la intención no captura.

**d) Se reemplaza el clasificador sin tocar la seguridad.** El comando `--ml`
cambia una clase entera —de reglas a Naive Bayes— y las garantías de seguridad
del sistema no se mueven un milímetro. Eso sólo es posible si el validador no
comparte estado con el clasificador.

### Qué valida, concretamente

| # | chequeo | ejemplo bloqueado |
|---|---|---|
| 1 | palabras peligrosas en el texto original | `salta desde la mesa`, `avanzá 2 metros saltando` |
| 2 | parámetros negativos | `avanzá -2 metros` |
| 3 | velocidad > `perfil.velocidad_max` (0.20 m/s) | `muévete a 2 m/s` |
| 4 | distancia > 5 m (largo útil de un aula) | `avanzá 100 metros` |
| 5 | ángulo > 180° | `girá 270 grados` |
| 6 | batería < 25 %, si hay telemetría real | movimiento con robot descargado |

Los límites 3 y 6 **no están escritos a mano**: salen de `perfil("tp07")` en
`sim/safety.py`. Es deliberado. Un número duplicado es un número que en algún
momento va a divergir del original, y el original acá es el que también aplica
el robot. Por la misma razón el extractor traduce *"rápido"* a
`perfil.velocidad_max` y no a un `0.5` fijo: si mañana el perfil baja a 0.15,
"rápido" baja solo, en vez de quedar un valor viejo esperando que el validador
lo ataje.

### Defensa en profundidad

El validador es la última barrera **del agente**, no del sistema. Abajo hay dos
capas más que no dependen de mi código: el `Ejecutor` recorta la velocidad al
máximo del perfil, y `sim/safety.py` **rechaza** (no recorta) cualquier valor
fuera de límite lanzando `ErrorDeSeguridad`, con la misma política para el
simulador y para el robot físico. Si un comando llega hasta ahí, significa que
mi validador dejó pasar algo que no debía: la tercera capa existe justamente
porque se asume que las dos primeras pueden fallar.

## 5. Decisiones de diseño discutibles

Tres, que defiendo pero que podrían resolverse distinto:

**DETENERSE tiene prioridad absoluta.** Si el texto contiene una orden de
frenar, no importa qué más diga. Es la única intención cuyo falso positivo es
barato (el robot se queda quieto) y cuyo falso negativo es caro. Costo asumido:
`avanzá 2 metros y después pará` frena sin avanzar.

**Entre las demás gana la que aparece primero.** `girá 45° y después avanzá`
ejecuta el giro. Prefiero hacer la mitad de lo pedido antes que adivinar cuál de
las dos órdenes importaba. La confianza baja a 0.65 para dejar registro de que
se ignoró algo.

**"hola" solo no es SALUDO.** SALUDO es la orden de que el robot salude
(*"saluda a los estudiantes"*); *"hola, ¿cómo te llamás?"* es alguien
conversando, y eso está fuera del dominio: DESCONOCIDO. Confundirlos haría que
el robot levante la mano cada vez que alguien lo saluda al pasar. El caso 9 del
JSON confirma esta lectura.

## 6. Una inconsistencia del material provisto

`casos_prueba.json` espera para `avanzá rápido 3 metros` el parámetro
`velocidad_ms: 0.5` **y** resultado `EJECUTAR`. Las dos cosas no pueden ser
ciertas a la vez: el perfil `tp07` tope la velocidad en **0.20 m/s**, así que un
0.5 tiene que ser bloqueado. Los valores del JSON vienen del enunciado en PDF,
que trabaja con un máximo de 0.5 m/s; el entorno real usa 0.20.

Resolví traduciendo *"rápido"* a `perfil.velocidad_max` (0.20) y *"despacio"* a
la mitad (0.10). Con eso el resultado es `EJECUTAR`, como pide el JSON, y el
comando es seguro bajo el perfil real. Es la única lectura que satisface las dos
fuentes. El evaluador de la cátedra compara resultados, no parámetros, así que
la diferencia no afecta la nota; la documento porque afecta el comportamiento.

## 7. Contenidos de la materia que aparecen

- **Agentes inteligentes:** percepción (texto) → razonamiento (pipeline) →
  acción (SDK), con el entorno como fuente de restricciones.
- **IA simbólica vs. subsimbólica:** implementadas las dos y comparadas sobre el
  mismo conjunto; la simbólica gana en auditabilidad y en comportamiento fuera
  de distribución, que es lo que pesa en un entorno de seguridad crítica.
- **Representación del conocimiento:** las regex son una base de reglas y las
  seis intenciones una ontología mínima del dominio robótico.
- **Evaluación de modelos:** accuracy/precision/recall/F1 sobre partición
  retenida, y análisis de falsos negativos en los comandos peligrosos como caso
  crítico —el error que no se puede cometer.
- **Seguridad en sistemas de IA:** validación post-clasificación obligatoria,
  fail-closed en telemetría, y defensa en profundidad en tres capas.

## 8. Conclusión

El agente alcanza 100 % de accuracy sobre los 25 casos y bloquea los 3
peligrosos. Ese número no es lo interesante: lo interesante es que **el mismo
100 % se sostiene con un clasificador que confunde "empujá la caja" con un
saludo**, porque la seguridad no depende de él.

Ahí está el punto del TP. Un sistema de IA que actúa sobre el mundo físico no se
hace seguro mejorando el modelo, se hace seguro poniéndole una capa que no
confíe en el modelo. El clasificador se va a equivocar —el mío se equivocó en
seis formas distintas apenas lo probé fuera del conjunto de prueba—. La
diferencia entre un sistema usable y uno que sólo anda en condiciones
controladas es qué pasa cuando eso ocurre.
