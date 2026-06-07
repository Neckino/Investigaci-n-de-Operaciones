import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from data import PLANTAS, CLIENTES, CENTROS


# Paleta fija y clara
COLOR_PLANTA  = "#4A90D9"
COLOR_CENTRO  = "#E67E22"
COLOR_CLIENTE = "#27AE60"
COLOR_CERRADO = "#BDC3C7"


def graficar(sol: dict, guardar_como: str = "red_logistica.png") -> None:
    if not sol["factible"]:
        print("Sin solución factible — no se genera gráfico.")
        return

    G = nx.DiGraph()

    P = [p.id for p in PLANTAS]
    C = [c.id for c in CLIENTES]
    D = [d.id for d in CENTROS]
    abiertos = sol["centros_abiertos"]

    G.add_nodes_from(P)
    G.add_nodes_from(D)
    G.add_nodes_from(C)

    # Arcos con peso = flujo
    for (p, d), v in sol["flujo_planta_cd"].items():
        G.add_edge(p, d, weight=v, tramo="P→CD")

    for (d, c), v in sol["flujo_cd_cliente"].items():
        G.add_edge(d, c, weight=v, tramo="CD→C")

    # Layout manual en tres columnas
    pos = {}
    n_p = len(P)
    for i, p in enumerate(P):
        pos[p] = (0, -(i - (n_p - 1) / 2) * 2)

    n_d = len(D)
    for i, d in enumerate(D):
        pos[d] = (3, -(i - (n_d - 1) / 2) * 3)

    n_c = len(C)
    for i, c in enumerate(C):
        pos[c] = (6, -(i - (n_c - 1) / 2) * 1.6)

    # Colores de nodos
    node_colors = []
    for n in G.nodes():
        if n in P:
            node_colors.append(COLOR_PLANTA)
        elif n in D:
            node_colors.append(COLOR_CENTRO if n in abiertos else COLOR_CERRADO)
        else:
            node_colors.append(COLOR_CLIENTE)

    # Grosor de arcos proporcional al flujo
    edges     = list(G.edges())
    weights   = [G[u][v]["weight"] for u, v in edges]
    max_w     = max(weights) if weights else 1
    widths    = [1 + 4 * (w / max_w) for w in weights]

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_facecolor("#F8F9FA")
    fig.patch.set_facecolor("#F8F9FA")

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=900,
        edgecolors="#2C3E50",
        linewidths=0.8,
    )
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_weight="bold", font_color="white")

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edgelist=edges,
        width=widths,
        edge_color="#5D6D7E",
        arrows=True,
        arrowsize=18,
        connectionstyle="arc3,rad=0.08",
        min_source_margin=22,
        min_target_margin=22,
    )

    # Etiquetas de flujo en arcos
    edge_labels = {(u, v): f"{G[u][v]['weight']:.0f}" for u, v in edges}
    nx.draw_networkx_edge_labels(
        G, pos, edge_labels=edge_labels,
        ax=ax, font_size=8, font_color="#2C3E50",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75),
    )

    # Anotaciones de oferta/demanda/déficit
    oferta_map  = {p.id: p.oferta  for p in PLANTAS}
    demanda_map = {c.id: c.demanda for c in CLIENTES}
    deficit_map = sol.get("deficit", {})

    for p in P:
        x_, y_ = pos[p]
        ax.annotate(f"oferta={oferta_map[p]}", xy=(x_, y_),
                    xytext=(x_ - 1.1, y_), fontsize=7.5,
                    color="#1A5276", ha="right",
                    arrowprops=dict(arrowstyle="-", color="#AEB6BF", lw=0.6))

    for c in C:
        x_, y_ = pos[c]
        dem = demanda_map[c]
        def_ = deficit_map.get(c, 0)
        label = f"dem={dem}" + (f"\n¡-{def_:.0f}!" if def_ > 0 else "")
        color = "#922B21" if def_ > 0 else "#1D6A39"
        ax.annotate(label, xy=(x_, y_),
                    xytext=(x_ + 0.9, y_), fontsize=7.5,
                    color=color, ha="left",
                    arrowprops=dict(arrowstyle="-", color="#AEB6BF", lw=0.6))

    # Leyenda
    leyenda = [
        mpatches.Patch(color=COLOR_PLANTA,  label="Planta (oferta)"),
        mpatches.Patch(color=COLOR_CENTRO,  label="CD abierto"),
        mpatches.Patch(color=COLOR_CERRADO, label="CD cerrado"),
        mpatches.Patch(color=COLOR_CLIENTE, label="Cliente (demanda)"),
    ]
    ax.legend(handles=leyenda, loc="upper left", fontsize=8.5,
              framealpha=0.9, edgecolor="#BDC3C7")

    costo = sol["costo_total"]
    rutas = len(sol["rutas_activas"])
    ax.set_title(
        f"Red de distribución óptima — Costo total: ${costo:,.2f}  |  Rutas activas: {rutas}/8",
        fontsize=11, fontweight="bold", color="#2C3E50", pad=14,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(guardar_como, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Gráfico guardado: {guardar_como}")
    