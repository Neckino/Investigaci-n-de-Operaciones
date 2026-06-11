import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
from data import PLANTAS, CLIENTES, CENTROS

# ── Paleta ────────────────────────────────────────────────────────────────────
BG          = "#F7F9FC"
COL_HDR     = "#1A3A5C"
C_PLANTA    = "#1A6EBD"
C_CLIENTE   = "#1E8449"
C_DEFICIT   = "#C0392B"
C_CERRADO   = "#BDC3C7"
C_ARCO_ACT  = "#1A6EBD"
C_ARCO_INA  = "#E0E4EA"
C_KPI_BG    = "#EAF2FB"
C_KPI_BDR   = "#D0DCF0"
C_TEXT      = "#2C3E50"
C_MUTED     = "#7F8C8D"


def _draw_node(ax, x, y, r, color, label, fontsize=9):
    circ = plt.Circle((x, y), r, color=color, zorder=5, clip_on=False,
                       linewidth=1.2, edgecolor="white")
    ax.add_patch(circ)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color="white", zorder=6)


def _draw_arrow(ax, x0, y0, x1, y1, lw, color, alpha=1.0):
    ax.annotate("",
        xy=(x1, y1), xytext=(x0, y0),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=lw,
            mutation_scale=12,
            alpha=alpha,
            connectionstyle="arc3,rad=0.0",
        ),
        zorder=3,
    )


def _kpi_card(ax, x, y, w, h, label, value, color, bg=C_KPI_BG):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.005",
                          fc=bg, ec=C_KPI_BDR, lw=0.8, zorder=2)
    ax.add_patch(rect)
    ax.text(x + 0.04, y + h * 0.62, label,
            ha="left", va="center", fontsize=7.8, color=C_MUTED)
    ax.text(x + w - 0.04, y + h * 0.28, value,
            ha="right", va="center", fontsize=10, fontweight="bold", color=color)


def graficar(sol: dict, guardar_como: str = "red_logistica.png") -> None:
    if not sol["factible"]:
        print("Sin solución factible — no se genera gráfico.")
        return

    P  = [p.id for p in PLANTAS]
    C  = [c.id for c in CLIENTES]
    D  = [d.id for d in CENTROS]

    oferta_m  = {p.id: p.oferta      for p in PLANTAS}
    demanda_m = {c.id: c.demanda     for c in CLIENTES}
    cap_m     = {d.id: d.capacidad   for d in CENTROS}
    flujo     = sol["flujo_directo"]          # {(p,c): v}
    deficit   = sol.get("deficit", {})
    abiertos  = sol["centros_abiertos"]
    d_sol     = sol["desglose"]
    n_rutas   = len(sol["rutas_directas"]) + len(sol["rutas_cd"])

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 8.5), facecolor=BG)
    gs  = GridSpec(1, 2, figure=fig,
                   width_ratios=[2.6, 1],
                   left=0.01, right=0.99,
                   top=0.93, bottom=0.04,
                   wspace=0.03)

    ax     = fig.add_subplot(gs[0])
    ax_kpi = fig.add_subplot(gs[1])
    ax.set_facecolor(BG)
    ax_kpi.set_facecolor(BG)
    ax_kpi.axis("off")

    # ── Coordenadas de nodos ──────────────────────────────────────────────────
    # Tres columnas: plantas (x=0.18), CDs (x=0.50), clientes (x=0.82)
    # Solo mostramos CDs si hay flujo pasando por ellos
    hay_cd = bool(sol["flujo_planta_cd"]) or bool(sol["flujo_cd_cliente"])

    XP, XD, XC = 0.18, 0.50, 0.82
    NODE_R = 0.042

    n_p, n_c, n_d = len(P), len(C), len(D)

    pos = {}
    for i, p in enumerate(P):
        pos[p] = (XP, 0.82 - i * (0.64 / max(n_p - 1, 1)))
    for i, c in enumerate(C):
        pos[c] = (XC, 0.88 - i * (0.76 / max(n_c - 1, 1)))
    for i, d in enumerate(D):
        pos[d] = (XD, 0.65 - i * 0.30)

    # ── Headers de columna ────────────────────────────────────────────────────
    for xv, lbl in [(XP, "Plantas"), (XC, "Clientes")]:
        ax.text(xv, 0.96, lbl, ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=COL_HDR,
                bbox=dict(boxstyle="round,pad=0.3", fc="#DDE8F5", ec="none"))

    if hay_cd:
        ax.text(XD, 0.96, "Centros de distribución", ha="center", va="center",
                fontsize=10.5, fontweight="bold", color=COL_HDR,
                bbox=dict(boxstyle="round,pad=0.3", fc="#DDE8F5", ec="none"))

    # Líneas guía verticales sutiles
    for xv in [XP, XC]:
        ax.axvline(xv, ymin=0.02, ymax=0.90,
                   color="#D5DCE8", lw=0.6, ls="--", alpha=0.5, zorder=0)

    # ── Arcos inactivos (todos los P→C que no se usan) ────────────────────────
    for p in P:
        for c in C:
            if (p, c) not in flujo:
                x0, y0 = pos[p]
                x1, y1 = pos[c]
                ax.plot([x0 + NODE_R, x1 - NODE_R], [y0, y1],
                        color=C_ARCO_INA, lw=0.7, alpha=0.6, zorder=1)

    # ── Arcos activos ─────────────────────────────────────────────────────────
    max_v = max(flujo.values()) if flujo else 1

    for (p, c), v in flujo.items():
        x0, y0 = pos[p]
        x1, y1 = pos[c]
        lw = 1.2 + 4.5 * (v / max_v)

        _draw_arrow(ax, x0 + NODE_R * 1.1, y0,
                        x1 - NODE_R * 1.1, y1,
                        lw=lw, color=C_ARCO_ACT)

        # Etiqueta de flujo — desplazada verticalmente para evitar solapamiento
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2 + 0.015
        ax.text(mx, my, f"{v:.0f} u.",
                ha="center", va="bottom",
                fontsize=8, fontweight="bold", color="#0D3B6E",
                bbox=dict(boxstyle="round,pad=0.18",
                          fc="white", ec="#C8D8ED", lw=0.7, alpha=0.95),
                zorder=7)

    # ── Nodos CDs (solo si hay flujo vía CD) ─────────────────────────────────
    if hay_cd:
        for d in D:
            color = C_PLANTA if d in abiertos else C_CERRADO
            _draw_node(ax, *pos[d], NODE_R, color, d)
            estado = "Abierto" if d in abiertos else "Cerrado"
            ax.text(pos[d][0], pos[d][1] - NODE_R - 0.035,
                    f"Cap: {cap_m[d]:.0f} u. · {estado}",
                    ha="center", va="top", fontsize=7.5, color=C_MUTED)

    # ── Nodos plantas ─────────────────────────────────────────────────────────
    for p in P:
        x, y = pos[p]
        _draw_node(ax, x, y, NODE_R, C_PLANTA, p)
        # Oferta a la izquierda
        ax.text(x - NODE_R - 0.025, y,
                f"Oferta: {oferta_m[p]:.0f} u.",
                ha="right", va="center",
                fontsize=8.5, color=COL_HDR,
                fontweight="semibold")

    # ── Nodos clientes ────────────────────────────────────────────────────────
    for c in C:
        x, y = pos[c]
        dem  = demanda_m[c]
        def_ = deficit.get(c, 0)
        rec  = dem - def_
        color = C_DEFICIT if def_ > 0 else C_CLIENTE

        _draw_node(ax, x, y, NODE_R, color, c)

        # Etiqueta a la derecha
        if def_ > 0:
            linea1 = f"Dem: {dem:.0f} u."
            linea2 = f"Rec: {rec:.0f}  Déf: {def_:.0f} u."
            ax.text(x + NODE_R + 0.025, y + 0.022, linea1,
                    ha="left", va="center", fontsize=8.5,
                    color=COL_HDR, fontweight="semibold")
            ax.text(x + NODE_R + 0.025, y - 0.022, linea2,
                    ha="left", va="center", fontsize=8,
                    color=C_DEFICIT)
        else:
            ax.text(x + NODE_R + 0.025, y,
                    f"Dem: {dem:.0f} u.",
                    ha="left", va="center",
                    fontsize=8.5, color=COL_HDR,
                    fontweight="semibold")

    # ── Leyenda inferior ──────────────────────────────────────────────────────
    leyenda = [
        mpatches.Patch(color=C_ARCO_ACT, label="Ruta activa"),
        mpatches.Patch(color=C_ARCO_INA, label="Ruta inactiva"),
        mpatches.Patch(color=C_DEFICIT,  label="Cliente con déficit"),
        mpatches.Patch(color=C_CLIENTE,  label="Cliente satisfecho"),
    ]
    ax.legend(handles=leyenda, loc="lower center",
              ncol=4, fontsize=8, framealpha=0.9,
              edgecolor=C_KPI_BDR,
              bbox_to_anchor=(0.5, -0.01))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Panel KPI ─────────────────────────────────────────────────────────────
    ax_kpi.set_xlim(0, 1)
    ax_kpi.set_ylim(0, 1)

    # Título panel
    ax_kpi.text(0.5, 0.97, "Resumen", ha="center", va="top",
                fontsize=11, fontweight="bold", color=COL_HDR)
    ax_kpi.axhline(0.93, color=C_KPI_BDR, lw=1.0)

    # Costo total destacado
    rect_top = FancyBboxPatch((0.05, 0.83), 0.90, 0.088,
                              boxstyle="round,pad=0.01",
                              fc="#1A3A5C", ec="none", zorder=2)
    ax_kpi.add_patch(rect_top)
    ax_kpi.text(0.50, 0.895, "Costo total",
                ha="center", va="center", fontsize=8.5, color="#A8C4E0")
    ax_kpi.text(0.50, 0.852, f"${sol['costo_total']:,.0f}",
                ha="center", va="center", fontsize=16,
                fontweight="bold", color="white")

    # Tarjetas KPI
    kpis = [
        ("Transporte",        f"${d_sol['transporte_directo']:,.0f}",  C_PLANTA),
        ("Penalizaciones",    f"${d_sol['penalizaciones']:,.0f}",       C_DEFICIT),
        ("CDs abiertos",      f"{len(abiertos)} / {len(D)}",           C_CERRADO),
        ("Rutas activas",     f"{n_rutas} / 8",                        C_PLANTA),
        ("Déficit total",     f"{sum(deficit.values()):.0f} u.",        C_DEFICIT),
        ("Oferta disponible", "400 u.",                                 C_MUTED),
        ("Demanda total",     "475 u.",                                 C_MUTED),
    ]

    y0_kpi = 0.785
    h_card = 0.088
    gap    = 0.012

    for i, (label, valor, color) in enumerate(kpis):
        yc = y0_kpi - i * (h_card + gap)
        bg = C_KPI_BG if i % 2 == 0 else "white"
        _kpi_card(ax_kpi, 0.05, yc, 0.90, h_card, label, valor, color, bg)

    # Donut de costos
    y_donut = y0_kpi - len(kpis) * (h_card + gap) - 0.04
    if y_donut > 0.12:
        vals   = [d_sol['transporte_directo'], d_sol['penalizaciones']]
        colors = [C_PLANTA, C_DEFICIT]
        labels = ["Transporte", "Penaliz."]

        ax_donut = ax_kpi.inset_axes(
            [0.05, y_donut - 0.17, 0.90, 0.20]
        )
        wedges, _ = ax_donut.pie(
            vals, colors=colors, startangle=90,
            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5)
        )
        ax_donut.set_title("Desglose de costos",
                           fontsize=8, color=COL_HDR, pad=4)
        ax_donut.legend(
            wedges, [f"{l}: ${v:,.0f}" for l, v in zip(labels, vals)],
            loc="lower center", fontsize=7,
            bbox_to_anchor=(0.5, -0.28), ncol=1,
            framealpha=0, edgecolor="none"
        )

    # Nota solver
    ax_kpi.text(0.5, 0.01, "CBC solver (PuLP) · Optimal",
                ha="center", va="bottom",
                fontsize=7, color=C_MUTED, style="italic")

    # ── Título global ─────────────────────────────────────────────────────────
    fig.suptitle(
        "Red de distribución logística — Solución óptima",
        fontsize=14, fontweight="bold", color=COL_HDR, y=0.99
    )

    plt.savefig(guardar_como, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"  Gráfico guardado: {guardar_como}")
    