import os
import platform
import subprocess

import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.gridspec import GridSpec
import numpy as np
from data import PLANTAS, CLIENTES, CENTROS

# ── Paleta ────────────────────────────────────────────────────────────────────
C_PLANTA   = "#1A6EBD"
C_CLIENTE  = "#1E8449"
C_DEFICIT  = "#C0392B"
C_CERRADO  = "#AAB7B8"
C_BG       = "#FAFAFA"
C_EDGE     = "#1A6EBD"
C_EDGE_DIM = "#D5D8DC"


def _pos_sin_cruce(plantas, clientes):
    """Posiciones verticales para plantas y clientes que minimicen cruces."""
    pos = {}
    n_p, n_c = len(plantas), len(clientes)
    for i, p in enumerate(plantas):
        pos[p] = (0.0, 1.0 - i / max(n_p - 1, 1))
    for i, c in enumerate(clientes):
        pos[c] = (1.0, 1.0 - i / max(n_c - 1, 1))
    return pos


def graficar(sol: dict, guardar_como: str = "red_logistica.png") -> None:
    if not sol["factible"]:
        print("Sin solución factible — no se genera gráfico.")
        return

    P = [p.id for p in PLANTAS]
    C = [c.id for c in CLIENTES]
    oferta_map  = {p.id: p.oferta  for p in PLANTAS}
    demanda_map = {c.id: c.demanda for c in CLIENTES}
    deficit_map = sol.get("deficit", {})
    flujo       = sol["flujo_directo"]   # {(p,c): v}

    # ── Figura con dos paneles: red (izq) + KPIs (der) ────────────────────────
    fig = plt.figure(figsize=(15, 8), facecolor=C_BG)
    gs  = GridSpec(1, 2, figure=fig, width_ratios=[3, 1], wspace=0.04)
    ax  = fig.add_subplot(gs[0])
    ax_kpi = fig.add_subplot(gs[1])
    ax.set_facecolor(C_BG)
    ax_kpi.set_facecolor(C_BG)
    ax_kpi.axis("off")

    # ── Layout manual en espacio [0,1]×[0,1] ─────────────────────────────────
    # Plantas y clientes en columnas; dejar margen para etiquetas
    margin_l, margin_r = 0.22, 0.18
    n_p, n_c = len(P), len(C)

    pos = {}
    for i, p in enumerate(P):
        y = 0.85 - i * (0.70 / (n_p - 1))
        pos[p] = (margin_l, y)
    for i, c in enumerate(C):
        y = 0.90 - i * (0.80 / (n_c - 1))
        pos[c] = (1 - margin_r, y)

    # ── Arcos ─────────────────────────────────────────────────────────────────
    max_flujo = max(flujo.values()) if flujo else 1

    # Dibujar primero arcos inactivos (todos los posibles P→C no usados)
    for p in P:
        for c in C:
            if (p, c) not in flujo:
                x0, y0 = pos[p]
                x1, y1 = pos[c]
                ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-", color=C_EDGE_DIM,
                                    lw=0.4, alpha=0.25))

    # Dibujar arcos activos con grosor proporcional al flujo
    for (p, c), v in sorted(flujo.items()):
        x0, y0 = pos[p]
        x1, y1 = pos[c]
        lw = 1.5 + 5.0 * (v / max_flujo)
        ax.annotate("", xy=(x1 - 0.01, y1), xytext=(x0 + 0.01, y0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=C_EDGE,
                lw=lw,
                mutation_scale=14,
                alpha=0.85,
            ))
        # Etiqueta de flujo en el punto medio, con fondo blanco
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ax.text(mx, my, f"{v:.0f} u.", fontsize=8.5, ha="center", va="center",
                color="#1A3A5C", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#D5D8DC",
                          lw=0.6, alpha=0.92))

    # ── Nodos plantas ─────────────────────────────────────────────────────────
    NODE_R = 0.038
    for p in P:
        x, y = pos[p]
        circ = plt.Circle((x, y), NODE_R, color=C_PLANTA, zorder=5, clip_on=False)
        ax.add_patch(circ)
        ax.text(x, y, p, ha="center", va="center", fontsize=9,
                fontweight="bold", color="white", zorder=6)
        # Etiqueta oferta a la izquierda
        ax.text(x - NODE_R - 0.015, y, f"Oferta: {oferta_map[p]:.0f} u.",
                ha="right", va="center", fontsize=8.5,
                color="#1A3A5C", style="italic")

    # ── Nodos clientes ────────────────────────────────────────────────────────
    for c in C:
        x, y = pos[c]
        dem  = demanda_map[c]
        def_ = deficit_map.get(c, 0)
        rec  = dem - def_
        color_nodo = C_DEFICIT if def_ > 0 else C_CLIENTE

        circ = plt.Circle((x, y), NODE_R, color=color_nodo, zorder=5, clip_on=False)
        ax.add_patch(circ)
        ax.text(x, y, c, ha="center", va="center", fontsize=9,
                fontweight="bold", color="white", zorder=6)

        # Etiqueta demanda a la derecha
        if def_ > 0:
            etiq = f"Dem: {dem:.0f} u.\nRec: {rec:.0f} u.  Déf: {def_:.0f} u."
            color_etiq = C_DEFICIT
        else:
            etiq = f"Dem: {dem:.0f} u."
            color_etiq = "#1E5631"
        ax.text(x + NODE_R + 0.015, y, etiq,
                ha="left", va="center", fontsize=8.5,
                color=color_etiq, style="italic",
                linespacing=1.5)

    # ── Títulos de columna ────────────────────────────────────────────────────
    ax.text(margin_l, 0.97, "Plantas", ha="center", va="bottom",
            fontsize=10, fontweight="bold", color="#1A3A5C")
    ax.text(1 - margin_r, 0.97, "Clientes", ha="center", va="bottom",
            fontsize=10, fontweight="bold", color="#1A3A5C")

    # Línea divisoria sutil
    for xv in [margin_l + 0.12, 1 - margin_r - 0.12]:
        ax.axvline(xv, color="#D5D8DC", lw=0.6, ls="--", alpha=0.5)

    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0.0, 1.02)
    ax.axis("off")
    ax.set_title("Red de distribución logística — solución óptima",
                 fontsize=13, fontweight="bold", color="#1A3A5C", pad=12)

    # ── Panel KPI ─────────────────────────────────────────────────────────────
    d = sol["desglose"]
    n_rutas = len(sol["rutas_directas"]) + len(sol["rutas_cd"])

    kpis = [
        ("Costo total",         f"${sol['costo_total']:,.0f}",  "#1A3A5C"),
        ("Transporte",          f"${d['transporte_directo']:,.0f}", "#1A6EBD"),
        ("Penalizaciones",      f"${d['penalizaciones']:,.0f}",  C_DEFICIT),
        ("CDs abiertos",        str(len(sol["centros_abiertos"])) + " / 2", C_CERRADO),
        ("Rutas activas",       f"{n_rutas} / 8",                C_PLANTA),
        ("Déficit total",       f"{sum(deficit_map.values()):.0f} u.", C_DEFICIT),
        ("Oferta disponible",   "400 u.",                         "#555"),
        ("Demanda total",       "475 u.",                         "#555"),
    ]

    ax_kpi.set_xlim(0, 1)
    ax_kpi.set_ylim(0, 1)

    ax_kpi.text(0.5, 0.97, "Resumen", ha="center", va="top",
                fontsize=11, fontweight="bold", color="#1A3A5C")

    sep_y = 0.91
    ax_kpi.axhline(sep_y, color="#D5D8DC", lw=0.8)

    y_start = 0.86
    step    = 0.105
    for i, (label, valor, color) in enumerate(kpis):
        y = y_start - i * step
        # Tarjeta de fondo alternada
        if i % 2 == 0:
            rect = mpatches.FancyBboxPatch(
                (0.04, y - 0.04), 0.92, 0.085,
                boxstyle="round,pad=0.01",
                fc="#EAF2FB", ec="none", zorder=0
            )
            ax_kpi.add_patch(rect)
        ax_kpi.text(0.08, y + 0.02, label, ha="left", va="center",
                    fontsize=8.5, color="#555")
        ax_kpi.text(0.92, y + 0.02, valor, ha="right", va="center",
                    fontsize=9.5, fontweight="bold", color=color)

    # Nota al pie
    ax_kpi.text(0.5, 0.01,
                "CBC solver (PuLP)\nSolución: Optimal",
                ha="center", va="bottom", fontsize=7.5,
                color="#AAB7B8", style="italic")

    plt.savefig(
        guardar_como,
        dpi=180,
        bbox_inches="tight",
        facecolor=C_BG
    )

    ruta_absoluta = os.path.abspath(guardar_como)

    print("\nGráfico guardado en:")
    print(ruta_absoluta)

    plt.close()

    print("Sistema operativo:", platform.system())
    print("Existe archivo:", os.path.exists(ruta_absoluta))

    try:
        sistema = platform.system()

        if sistema == "Windows":
            os.startfile(ruta_absoluta)

        elif sistema == "Darwin":
            subprocess.run(["open", ruta_absoluta])

        else:
            subprocess.run(["xdg-open", ruta_absoluta])

    except Exception as e:
        print(f"No fue posible abrir automáticamente la imagen: {e}")
    