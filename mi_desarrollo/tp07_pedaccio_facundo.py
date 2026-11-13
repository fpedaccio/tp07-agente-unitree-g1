# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
#
#  Nombre y apellido:  Pedaccio, Facundo
#  Comision:           .....................................
#
#  Enfoque elegido: NIVEL 1 (reglas + expresiones regulares) como motor
#  principal, con NIVEL 2 (Naive Bayes sobre dataset.csv) disponible como
#  extension opcional -- se activa con la bandera --ml y reemplaza UNA
#  sola clase, ClasificadorIntencion. El extractor, el validador y el
#  ejecutor no se enteran del cambio.
#
#  Uso:
#      python3 tp07_pedaccio_facundo.py --sin-robot     evalua los 25 casos
#      python3 tp07_pedaccio_facundo.py                 con simulador abierto
#      python3 tp07_pedaccio_facundo.py --sin-robot --ml  usa el modelo ML
# =====================================================================

import re
import unicodedata

from robot import Robot

from ejecutor import Ejecutor
from evaluar import evaluar

# Pone tu nombre: aparece en el reporte que entregas.
ALUMNO = "Pedaccio, Facundo"


# =====================================================================
#  NORMALIZACION - compartida por las tres etapas
# =====================================================================
def normalizar(texto):
    """Minusculas, sin tildes y con los signos convertidos en espacios.

    Es lo primero que hace cada etapa. Sacar las tildes resuelve de una
    vez el problema morfologico del rioplatense: "avanza" y "avanza",
    "gira" y "gira", "para" y "para" pasan a ser la misma cadena y cada
    intencion necesita UN patron en vez de dos o tres. Los signos "!?,."
    se vuelven espacios para que \b funcione en "¿cuanta bateria tenes?".
    """
    texto = (texto or "").lower().strip()
    # NFD separa la letra de su tilde; el filtro descarta las tildes.
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Se conservan el grado (unidad, no puntuacion), la barra de "m/s", la
    # coma y el punto decimales, y el signo menos: sacar el menos convertiria
    # "-2 metros" en "2 metros" y el validador nunca se enteraria.
    texto = re.sub(r"[^\w\s°/.,-]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# =====================================================================
#  ETAPA 1 - CLASIFICADOR DE INTENCION
# =====================================================================
class ClasificadorIntencion:
    """Decide QUE quiere el usuario, sin mirar los numeros todavia.

    Tres decisiones de diseno que vale la pena defender:

    1. DETENERSE tiene prioridad absoluta. Si el texto contiene una orden
       de frenar, no importa que mas diga: se frena. Es la unica intencion
       cuyo falso positivo es barato (el robot se queda quieto) y cuyo
       falso negativo es caro (el robot sigue andando cuando le pidieron
       que pare).

    2. Entre las demas gana la que aparece PRIMERO en el texto. "gira 45
       grados y despues avanza" son dos ordenes; el agente ejecuta la
       primera. Es honesto: preferimos hacer la mitad de lo que se pidio
       antes que adivinar cual de las dos importaba.

    3. "hola" solo NO es SALUDO. SALUDO es la orden de que el robot
       salude ("saluda a los estudiantes", "hace un saludo"); "hola,
       como te llamas?" es alguien conversando con el robot, y eso esta
       fuera del dominio: DESCONOCIDO. Confundirlos haria que el robot
       levante la mano cada vez que alguien lo saluda al pasar.
    """

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO",
             "CONSULTAR_ESTADO", "DESCONOCIDO")

    # --- Frenar: se evalua antes que todo lo demas -------------------
    # Ojo con "para": "para todo" frena, pero "anda para atras" NO. Por eso
    # el patron exige que "para" venga seguido de un cierre (todo/ya/ahi) o
    # sea el final de la orden, en vez de aceptar la palabra suelta.
    PATRONES_FRENO = (
        r"\bdeten",                      # detente, detener, detenete
        r"\bfren(a|ar|e|o)\b",           # frena, frenar, frene  (frena ahi)
        r"\bpar(a|ate)\s+(todo|ya|ahi|de\s+una)\b",
        r"\bpar(a|ate)\s+de\s+\w+",     # "para de girar" tambien es frenar
        r"\bdeja\s+de\s+\w+",           # "deja de caminar"
        r"\bpar(a|ate)\b\s*$",           # "para" como orden completa
        r"\bquieto\b", r"\balto\b", r"\bstop\b", r"\bbasta\b",
        r"\bno\s+te\s+muevas\b",
    )
    # Negacion de una accion = pedido de frenar. "no avances" es DETENERSE,
    # no un MOVER con el signo cambiado.
    PATRON_NEGACION = (r"\bno\s+(te\s+|me\s+|se\s+)?"
                       r"(avances|avanzes|avanzar|sigas|seguir|camines|camines|"
                       r"muevas|movas|moverte|vayas|arranques|gires|rotes|"
                       r"retrocedas|saludes|salude|frenes|pares|hagas)\b")

    # --- El resto de las intenciones ---------------------------------
    # El orden de la tupla NO decide nada: se elige por posicion en el
    # texto. Esta escrito de mas general a mas especifico solo para leerlo.
    PATRONES = (
        # "avanza" y "avances" se escriben distinto (z / c) y las dos son la
        # misma orden; "movete" (rioplatense) no lleva la u de "muevete".
        ("MOVER", r"\bavan[zc]|\bmuev|\bmov(e|a)|\bcamin|\bretroced|\bdesplaz"
                  r"|\bmarch|\band(a|ar|ate)\b|\badelante\b|\bpara\s+atras\b"),
        ("GIRAR", r"\bgir|\brot(a|ar|e)\b|\bvuelta\b|\bvolte(a|ar)\b"),
        ("SALUDO", r"\bsalud"),
        ("CONSULTAR_ESTADO", r"\bbateri|\bestado\b|\bstatus\b|\bcarga\b"
                             r"|\bnivel\b|\btelemetri|\bcomo\s+(estas|andas|"
                             r"venis|te\s+sentis)\b"),
    )
    # "hola" cuenta como SALUDO solo si hay un verbo que lo convierte en
    # orden: "hacele hola a la clase" si, "hola que tal" no.
    PATRON_HOLA_IMPERATIVO = (r"\b(hace|hacele|haceles|deci|decile|tirale|"
                              r"manda|mandale|dale|tira)\b[^.]*\bhola\b")

    def __init__(self, usar_modelo=False, ruta_dataset=None):
        self.modelo = None
        self.ultima_confianza = 0.0
        self.ultima_regla = ""

        # -------------------------------------------------------------
        #  NIVEL 2 (extension): el modelo entrenado sobre dataset.csv.
        #
        #  Se carga solo si lo piden, y si falla (no esta scikit-learn, o
        #  el dataset no existe) el agente sigue andando con las reglas.
        #  Un agente que controla hardware no puede quedarse mudo porque
        #  falto una dependencia opcional.
        # -------------------------------------------------------------
        if usar_modelo:
            try:
                from entrenar import entrenar_desde_csv
                if ruta_dataset:
                    self.modelo = entrenar_desde_csv(ruta_dataset)
                else:
                    self.modelo = entrenar_desde_csv()
            except Exception as exc:            # noqa: BLE001
                print(f"  [AVISO] No se pudo cargar el modelo ML ({exc}).")
                print("          El agente sigue con el clasificador de reglas.")

    # ---- API que usa el resto del pipeline --------------------------
    def clasificar(self, texto):
        """Devuelve uno de los seis tipos de TIPOS."""
        tipo, self.ultima_confianza, self.ultima_regla = self.explicar(texto)
        return tipo

    def explicar(self, texto):
        """Igual que clasificar(), pero devuelve (tipo, confianza, regla).

        La regla es la que disparo la decision: sirve para el analisis de
        fallos, que es medio imposible de hacer si el clasificador es una
        caja negra que solo devuelve una etiqueta.
        """
        t = normalizar(texto)
        if not t:
            return "DESCONOCIDO", 0.0, "texto vacio"

        # 1. Frenar gana siempre.
        for patron in self.PATRONES_FRENO:
            if re.search(patron, t):
                return "DETENERSE", 0.95, f"freno: {patron}"
        if re.search(self.PATRON_NEGACION, t):
            # Menos confianza: es una inferencia ("no hagas X" -> "para"),
            # no una orden literal. Igual se ejecuta, porque la accion que
            # se infiere es detenerse, que es la opcion segura.
            return "DETENERSE", 0.75, "negacion de una accion -> frenar"

        # 2. El modelo ML, si esta cargado, opina antes que las reglas.
        if self.modelo is not None:
            try:
                tipo = str(self.modelo.predict([texto])[0]).upper()
                if tipo in self.TIPOS and tipo != "DESCONOCIDO":
                    return tipo, 0.8, "modelo ML (naive bayes)"
                # Si el modelo dice DESCONOCIDO igual dejamos que las reglas
                # intenten: son mas precisas en el vocabulario del dominio.
            except Exception:                    # noqa: BLE001
                pass

        # 3. Reglas: gana la intencion que aparece primero en el texto.
        candidatas = []
        for tipo, patron in self.PATRONES:
            m = re.search(patron, t)
            if m:
                candidatas.append((m.start(), tipo, patron))
        if re.search(self.PATRON_HOLA_IMPERATIVO, t):
            candidatas.append((t.find("hola"), "SALUDO", "hola imperativo"))

        if not candidatas:
            return "DESCONOCIDO", 0.0, "ningun patron del dominio"

        posicion, tipo, patron = min(candidatas, key=lambda c: c[0])
        # Si hubo mas de una intencion, la confianza baja: acertamos la
        # primera, pero la orden tenia dos y estamos ignorando una.
        confianza = 0.9 if len({c[1] for c in candidatas}) == 1 else 0.65
        return tipo, confianza, f"{patron} (pos {posicion})"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Saca los numeros del texto. Sigue en unidades humanas: m y grados.

    Los adverbios ("despacio", "un poco") se resuelven contra el perfil de
    seguridad, no contra constantes escritas a mano. Si manana el perfil
    baja de 0.20 a 0.15 m/s, "rapido" baja solo: no queda un 0.5 viejo
    escondido en el codigo esperando a que el validador lo ataje.
    """

    # "2 metros" pero NO el "2" de "2 m/s": el lookahead descarta la barra.
    # El signo se captura a proposito: un "-2 metros" no se corrige en
    # silencio, se extrae tal cual y lo rechaza el validador. Corregirlo aca
    # seria adivinar si el usuario queria retroceder o si se equivoco.
    RE_DISTANCIA = r"(-?\d+(?:[.,]\d+)?)\s*(?:metros?|mts?\.?|m)\b(?!\s*/\s*s)"
    RE_ANGULO = r"(-?\d+(?:[.,]\d+)?)\s*(?:grados?|°)"
    RE_VELOCIDAD = r"(-?\d+(?:[.,]\d+)?)\s*m\s*/\s*s"
    RE_PASOS = r"(\d+)\s*pasos?\b"
    LARGO_DE_PASO_M = 0.5

    DISTANCIA_POR_DEFECTO_M = 0.5      # "avanza" sin numero: un paso corto

    def __init__(self, perfil):
        self.perfil = perfil

    def extraer(self, texto, tipo):
        t = normalizar(texto)
        p = {}

        # --- numeros explicitos --------------------------------------
        m = re.search(self.RE_VELOCIDAD, t)
        if m:
            p["velocidad_ms"] = self._numero(m.group(1))
        m = re.search(self.RE_DISTANCIA, t)
        if m:
            p["distancia_m"] = self._numero(m.group(1))
        m = re.search(self.RE_ANGULO, t)
        if m:
            p["angulo_deg"] = self._numero(m.group(1))

        # --- adverbios de velocidad (sin numero) ---------------------
        # Se usa setdefault: si el usuario dio un numero, el numero manda.
        # "avanza rapido a 0.1 m/s" avanza a 0.1, no a la maxima.
        if re.search(r"\bdespacio\b|\blento\b|\bsuave\b|\bcon\s+cuidado\b", t):
            p.setdefault("velocidad_ms", round(self.perfil.velocidad_max / 2, 3))
        elif re.search(r"\brapido\b|\bveloz\b|\bapurate\b|\bligero\b", t):
            # "rapido" es la maxima que permite el perfil, NUNCA mas.
            # Traducir un adverbio a un numero por encima del limite seria
            # fabricar un comando peligroso que el usuario no pidio.
            p.setdefault("velocidad_ms", self.perfil.velocidad_max)

        # "3 pasos" es una unidad de distancia como cualquier otra: la
        # persona no piensa en metros, piensa en pasos.
        m = re.search(self.RE_PASOS, t)
        if m:
            p.setdefault("distancia_m",
                         round(int(m.group(1)) * self.LARGO_DE_PASO_M, 2))

        # --- cantidades vagas de distancia ---------------------------
        if re.search(r"\bun\s+poco\b|\bun\s+toque\b|\bunos\s+pasos\b", t):
            p.setdefault("distancia_m", 0.5)
        elif re.search(r"\bbastante\b|\bbien\s+lejos\b", t):
            p.setdefault("distancia_m", 2.0)

        # --- angulos vagos -------------------------------------------
        if re.search(r"\bmedia\s+vuelta\b|\bdate\s+vuelta\b|\bal\s+reves\b", t):
            p.setdefault("angulo_deg", 180.0)
        elif re.search(r"\bvuelta\s+completa\b|\buna\s+vuelta\s+entera\b", t):
            # 360 no pasa el validador, y esta bien que no pase: el agente
            # no inventa un valor legal, deja que lo rechacen.
            p.setdefault("angulo_deg", 360.0)
        elif re.search(r"\bun\s+cuarto\s+de\s+vuelta\b", t):
            p.setdefault("angulo_deg", 90.0)

        # --- direccion ------------------------------------------------
        if re.search(r"\bderech(a|o)\b|\bright\b", t):
            p["direccion"] = "derecha"
        elif re.search(r"\bizquierd(a|o)\b|\bleft\b", t):
            p["direccion"] = "izquierda"
        elif tipo == "MOVER":
            if re.search(r"\bretroced|\batras\b|\bhacia\s+atras\b|\breversa\b", t):
                p["direccion"] = "atras"
            elif re.search(r"\badelante\b|\bde\s+frente\b", t):
                p["direccion"] = "adelante"

        # --- defaults por tipo ---------------------------------------
        if tipo == "MOVER":
            p.setdefault("distancia_m", self.DISTANCIA_POR_DEFECTO_M)
        elif tipo == "GIRAR":
            p.setdefault("angulo_deg", 90.0)
            p.setdefault("direccion", "derecha")
        return p

    # Referencias del tipo "hasta la puerta": el agente entiende el verbo,
    # pero no tiene mapa ni vision, asi que no puede convertirlas en metros.
    RE_REFERENCIA = r"\bhasta\s+(la|el|los|las)\s+(\w+)"

    def referencia_sin_resolver(self, texto, parametros):
        """Devuelve el punto de referencia que no se puede traducir a metros."""
        m = re.search(self.RE_REFERENCIA, normalizar(texto))
        if m and "distancia_m" not in self._explicitos(texto):
            return m.group(2)
        return None

    def _explicitos(self, texto):
        """Solo los parametros que el usuario escribio con numero."""
        t = normalizar(texto)
        p = {}
        if re.search(self.RE_DISTANCIA, t):
            p["distancia_m"] = True
        if re.search(self.RE_PASOS, t):
            p["distancia_m"] = True
        return p

    @staticmethod
    def _numero(txt):
        """"1,5" y "1.5" son el mismo numero: en castellano se escriben las dos."""
        return float(txt.replace(",", "."))


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    """La ultima barrera antes del robot.

    Componente SEPARADO del clasificador, y a proposito. El clasificador se
    va a equivocar: es un modelo, y los modelos se equivocan. Si la
    seguridad viviera adentro, un error de clasificacion seria tambien un
    error de seguridad. Separandolos, un error de clasificacion sigue
    siendo un comando bloqueado.

    De ahi que valide el TEXTO ORIGINAL y no solo la intencion: "salta
    desde la mesa" no lo entiende ningun clasificador, y justamente por eso
    hay que frenarlo. Si DESCONOCIDO saltease la validacion, el comando mas
    peligroso seria el unico que se escapa.
    """

    # Verbos de acciones que el robot no debe intentar nunca. Van sin tilde
    # porque el texto llega normalizado ("empuja" cubre tambien "empuja").
    PALABRAS_PELIGROSAS = (
        # \w* y no \b: "salta" tiene que bloquear tambien "saltando" y
        # "saltito". Un peligro en gerundio sigue siendo el mismo peligro.
        r"\bsalt\w*", r"\bsprint\w*",
        # "corr" no puede ir con \w*: se comeria "corregi el rumbo", que es
        # una orden legitima. Por eso van las terminaciones una por una.
        r"\bcorr(e|es|en|er|iendo|amos|an|ele)\b",
        r"\bempuj\w*", r"\bgolpe\w*", r"\bromp\w*", r"\bpate\w*",
        r"\btir(a|ar|ate|arse|ando|alo)\b", r"\bca(e|ete|erse|yendo)\b",
        r"\bfuerza\b",
        r"\bbackflip\b", r"\bpirueta\b", r"\bvoltereta\b", r"\bmortal\b",
        r"\btrep(a|ar)\b", r"\bbaja\s+la\s+escalera\b",
    )

    # No viene del perfil: el perfil habla de velocidad y tiempo, no de
    # cuanto tiene sentido caminar. 5 m es el largo util de un aula.
    DISTANCIA_MAX_M = 5.0
    ANGULO_MAX_DEG = 180.0

    def __init__(self, perfil):
        self.perfil = perfil

    def validar(self, texto, tipo, parametros, bateria=None):
        """Devuelve (True, "") si se puede ejecutar, o (False, motivo)."""
        t = normalizar(texto)
        p = parametros or {}

        # 1. Palabras peligrosas en el TEXTO ORIGINAL, entienda o no el
        #    clasificador. Esta es la regla que atrapa los DESCONOCIDO
        #    peligrosos, que son los que mas importan.
        for patron in self.PALABRAS_PELIGROSAS:
            m = re.search(patron, t)
            if m:
                return False, (f"accion no permitida: '{m.group(0)}' describe "
                               f"un movimiento que el robot no debe intentar")

        # 2. Numeros negativos. No hay lectura sensata de "-2 metros": puede
        #    ser "retroceder 2" o un error de tipeo, y el agente no adivina
        #    cual cuando el que se mueve es un robot de 35 kg.
        for clave in ("distancia_m", "angulo_deg", "velocidad_ms"):
            if clave in p and float(p[clave]) < 0:
                return False, (f"{clave} = {p[clave]:g} es negativo; "
                               f"deci la direccion en palabras: "
                               f"'retroceder 2 metros', 'girar a la izquierda')")

        # 3. Velocidad pedida por encima del perfil de la materia.
        if "velocidad_ms" in p:
            v = abs(float(p["velocidad_ms"]))
            if v > self.perfil.velocidad_max + 1e-9:
                return False, (f"velocidad {v:g} m/s excede el maximo de "
                               f"{self.perfil.velocidad_max:g} m/s")

        # 4. Distancia sin sentido para un aula.
        if tipo == "MOVER":
            d = abs(float(p.get("distancia_m", 0.0)))
            if d > self.DISTANCIA_MAX_M:
                return False, (f"distancia {d:g} m excede el maximo de "
                               f"{self.DISTANCIA_MAX_M:g} m en el aula")

        # 5. Angulo mayor a media vuelta: siempre hay un giro equivalente
        #    mas corto, asi que pedir 270 grados es un error de quien habla.
        if tipo == "GIRAR":
            a = abs(float(p.get("angulo_deg", 0.0)))
            if a > self.ANGULO_MAX_DEG:
                return False, (f"angulo {a:g}° excede el maximo de "
                               f"{self.ANGULO_MAX_DEG:g}° (gira para el otro lado)")

        # 6. Bateria. Solo se chequea si hay telemetria real; sin robot
        #    conectado no hay numero que mirar. En el robot, ademas, la capa
        #    de sim.safety es fail-closed: bateria desconocida = bloqueado.
        if bateria is not None and tipo in ("MOVER", "GIRAR"):
            if float(bateria) < self.perfil.bateria_min:
                return False, (f"bateria {bateria}% por debajo del minimo de "
                               f"{self.perfil.bateria_min}%")

        return True, ""


# =====================================================================
#  EL AGENTE - une las tres etapas y llama al ejecutor
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None, usar_modelo=False):
        self.robot = robot
        perfil = robot.perfil if robot else _perfil_por_defecto()
        self.perfil = perfil
        self.clasificador = ClasificadorIntencion(usar_modelo=usar_modelo)
        self.extractor = ExtractorParametros(perfil)
        self.validador = ValidadorSeguridad(perfil)
        self.ejecutor = Ejecutor(robot) if robot else None
        self.historial = []

    def procesar(self, texto):
        """El pipeline completo: clasificar -> extraer -> validar -> ejecutar."""
        # --- 1. clasificar -------------------------------------------
        tipo, confianza, regla = self.clasificador.explicar(texto)

        # --- 2. extraer ----------------------------------------------
        parametros = self.extractor.extraer(texto, tipo)

        # --- 3. validar (SIEMPRE, aunque el tipo sea DESCONOCIDO) -----
        ok, motivo = self.validador.validar(texto, tipo, parametros,
                                            bateria=self._bateria())
        if not ok:
            return self._resultado(texto, tipo, parametros, confianza, regla,
                                   ejecutar=False, bloqueado=True,
                                   mensaje=f"BLOQUEADO: {motivo}")

        # --- 3b. ambiguedad: se entendio el verbo, pero no el destino --
        # "anda hasta la puerta" es una orden perfectamente clara para una
        # persona e imposible para este agente: no tiene mapa ni camara. La
        # alternativa seria avanzar los 0.5 m por defecto "hacia la puerta",
        # que es peor que no hacer nada, porque parece obediencia.
        if tipo == "MOVER":
            referencia = self.extractor.referencia_sin_resolver(texto, parametros)
            if referencia:
                return self._resultado(
                    texto, "DESCONOCIDO", parametros, 0.3,
                    f"{regla} + referencia espacial sin resolver",
                    ejecutar=False, bloqueado=False,
                    mensaje=f"entendi que querias avanzar, pero no se donde "
                            f"esta '{referencia}': no tengo mapa. Deci cuantos "
                            f"metros ('avanza 2 metros')")

        # --- 4. ejecutar ---------------------------------------------
        if tipo == "DESCONOCIDO":
            # No se entendio y no habia nada peligroso: se avisa y no se
            # ejecuta nada. DESCONOCIDO es una respuesta correcta.
            return self._resultado(
                texto, tipo, parametros, confianza, regla,
                ejecutar=False, bloqueado=False,
                mensaje="no entendi el comando. Proba: 'avanza 2 metros', "
                        "'gira 90 grados a la derecha', 'detente', "
                        "'saluda', '¿cuanta bateria tenes?'")

        if self.ejecutor is None:
            mensaje = f"(sin robot) {tipo} {parametros}"
        else:
            mensaje = self.ejecutor.ejecutar(tipo, parametros)

        return self._resultado(texto, tipo, parametros, confianza, regla,
                               ejecutar=True, bloqueado=False, mensaje=mensaje)

    # ---- auxiliares --------------------------------------------------
    def _bateria(self):
        """Telemetria real si hay robot; None si estamos en --sin-robot."""
        if self.robot is None:
            return None
        try:
            estado = self.robot.verificar_estado()
            return getattr(estado, "bateria", None)
        except Exception:                        # noqa: BLE001
            # Sin telemetria confiable no se inventa un numero: se devuelve
            # None y el validador no puede afirmar que la bateria alcanza.
            return None

    def _resultado(self, texto, tipo, parametros, confianza, regla,
                   ejecutar, bloqueado, mensaje):
        r = {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": ejecutar,
            "bloqueado": bloqueado,
            "confianza": confianza,
            "texto_original": texto,
            "mensaje": mensaje,
            "regla": regla,
        }
        self.historial.append(r)
        return r


def _perfil_por_defecto():
    """Permite evaluar el agente sin abrir el simulador."""
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


# =====================================================================
#  PROGRAMA PRINCIPAL
# =====================================================================
def main():
    import sys

    sin_robot = "--sin-robot" in sys.argv
    usar_modelo = "--ml" in sys.argv

    robot = None
    if not sin_robot:
        robot = Robot()
        robot.conectar()

    try:
        agente = AgenteRobot(robot, usar_modelo=usar_modelo)
        print(f"\n  Alumno: {ALUMNO}")
        print(f"  Clasificador: {'ML (naive bayes)' if agente.clasificador.modelo else 'reglas + regex'}")
        print(f"  Perfil de seguridad: {agente.perfil.nombre} "
              f"(vel max {agente.perfil.velocidad_max:g} m/s)")
        evaluar(agente)

        if robot is not None:
            print("\n  Escribi ordenes para el robot. Enter vacio para salir.")
            while True:
                try:
                    texto = input("\n  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    break
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot is not None:
            robot.detenerse()
            robot.desconectar()


if __name__ == "__main__":
    main()
