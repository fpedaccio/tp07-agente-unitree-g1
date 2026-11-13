# =====================================================================
#  EXTENSION (Nivel 2) - Reglas vs. clasificador ML
#
#  Corre el MISMO pipeline dos veces, cambiando una sola clase:
#  ClasificadorIntencion. El extractor, el validador y el ejecutor son
#  identicos en las dos corridas. Esa es toda la evidencia que hace falta
#  para defender la arquitectura modular: si las etapas estuvieran
#  acopladas, este archivo no podria existir.
#
#      python3 comparar_ml.py
#
#  Ademas escribe REPORTE_ACCURACY.md con la tabla de los 25 casos.
# =====================================================================

import json
from collections import Counter
from pathlib import Path

from evaluar import cargar_casos, evaluar
from tp07_pedaccio_facundo import AgenteRobot, ALUMNO

AQUI = Path(__file__).resolve().parent
REPORTE = AQUI.parent / "REPORTE_ACCURACY.md"


def correr(usar_modelo):
    agente = AgenteRobot(None, usar_modelo=usar_modelo)
    if usar_modelo and agente.clasificador.modelo is None:
        return None, None
    resumen = evaluar(agente, mostrar=False)
    detalle = [agente.procesar(c["texto"]) for c in cargar_casos()]
    return resumen, detalle


def metricas_intencion(casos, detalle):
    """Accuracy de la INTENCION (no del resultado): mide solo el clasificador."""
    aciertos = sum(d["tipo"] == c["intencion_esperada"]
                   for c, d in zip(casos, detalle))
    return aciertos / len(casos)


def tabla_markdown(casos, resumen, detalle):
    filas = ["| # | texto | esperado | obtenido | intención | ok |",
             "|---|---|---|---|---|---|"]
    for c, f, d in zip(casos, resumen["filas"], detalle):
        marca = "✅" if f["correcto"] else "❌"
        peligro = " ⚠️" if f["peligroso"] else ""
        filas.append(f"| {c['id']}{peligro} | `{c['texto']}` | {f['esperado']} "
                     f"| {f['obtenido']} | {d['tipo']} | {marca} |")
    return "\n".join(filas)


def main():
    casos = cargar_casos()
    r_reglas, d_reglas = correr(usar_modelo=False)
    r_ml, d_ml = correr(usar_modelo=True)

    print("\n  REGLAS vs. MODELO ML sobre los mismos 25 casos")
    print("  " + "=" * 60)
    print(f"  {'':<22} {'resultado':>10} {'intencion':>10}")
    print(f"  {'reglas + regex':<22} {r_reglas['accuracy']*100:>9.1f}% "
          f"{metricas_intencion(casos, d_reglas)*100:>9.1f}%")
    if r_ml is None:
        print(f"  {'naive bayes':<22} {'no disponible (falta scikit-learn)':>10}")
    else:
        print(f"  {'naive bayes':<22} {r_ml['accuracy']*100:>9.1f}% "
              f"{metricas_intencion(casos, d_ml)*100:>9.1f}%")
        print(f"\n  Peligrosos bloqueados - reglas: "
              f"{r_reglas['peligrosos_bloqueados']}/{r_reglas['peligrosos_totales']}"
              f"   ML: {r_ml['peligrosos_bloqueados']}/{r_ml['peligrosos_totales']}")
        print("  (los bloquea el validador, que es el mismo en las dos corridas:")
        print("   por eso el numero no cambia aunque el clasificador sea peor)")

        difs = [(c["id"], c["texto"], a["tipo"], b["tipo"])
                for c, a, b in zip(casos, d_reglas, d_ml) if a["tipo"] != b["tipo"]]
        if difs:
            print(f"\n  Casos donde los dos clasificadores difieren ({len(difs)}):")
            for i, texto, a, b in difs:
                print(f"    {i:>3}. \"{texto}\"  reglas={a}  ml={b}")

    # --- reporte de accuracy que se entrega --------------------------
    partes = [
        "# TP07 — Reporte de accuracy",
        "",
        f"**Alumno:** {ALUMNO}  ",
        "**Archivo evaluado:** `mi_desarrollo/tp07_pedaccio_facundo.py`  ",
        "**Evaluador:** `mi_desarrollo/evaluar.py` (provisto por la cátedra, sin modificar)  ",
        "**Comando:** `python3 tp07_pedaccio_facundo.py --sin-robot`",
        "",
        "## Clasificador basado en reglas (entrega principal)",
        "",
        f"- **Accuracy sobre el resultado: {r_reglas['aciertos']}/{r_reglas['casos']} "
        f"= {r_reglas['accuracy']*100:.1f} %** (la consigna pide ≥ 70 %)",
        f"- **Accuracy sobre la intención: "
        f"{metricas_intencion(casos, d_reglas)*100:.1f} %**",
        f"- **Peligrosos bloqueados: {r_reglas['peligrosos_bloqueados']}/"
        f"{r_reglas['peligrosos_totales']}** (no se negocia: tiene que ser 100 %)",
        "",
        tabla_markdown(casos, r_reglas, d_reglas),
        "",
        "⚠️ = caso peligroso; el validador tiene que bloquearlo sí o sí.",
        "",
    ]
    if r_ml is not None:
        partes += [
            "## Extensión — clasificador ML (Naive Bayes, `dataset.csv`)",
            "",
            "Misma corrida, cambiando **solo** `ClasificadorIntencion`:",
            "",
            "| clasificador | accuracy resultado | accuracy intención | peligrosos bloqueados |",
            "|---|---|---|---|",
            f"| reglas + regex | {r_reglas['accuracy']*100:.1f} % | "
            f"{metricas_intencion(casos, d_reglas)*100:.1f} % | "
            f"{r_reglas['peligrosos_bloqueados']}/{r_reglas['peligrosos_totales']} |",
            f"| Naive Bayes (85 ejemplos) | {r_ml['accuracy']*100:.1f} % | "
            f"{metricas_intencion(casos, d_ml)*100:.1f} % | "
            f"{r_ml['peligrosos_bloqueados']}/{r_ml['peligrosos_totales']} |",
            "",
        ]
        difs = [(c["id"], c["texto"], a["tipo"], b["tipo"])
                for c, a, b in zip(casos, d_reglas, d_ml) if a["tipo"] != b["tipo"]]
        if difs:
            partes += ["Casos donde difieren:", "",
                       "| # | texto | reglas | ML |", "|---|---|---|---|"]
            partes += [f"| {i} | `{t}` | {a} | {b} |" for i, t, a, b in difs]
            partes.append("")
    REPORTE.write_text("\n".join(partes), encoding="utf-8")
    print(f"\n  Reporte escrito en {REPORTE}\n")


if __name__ == "__main__":
    main()
