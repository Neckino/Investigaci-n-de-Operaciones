from data import PLANTAS, CLIENTES, CENTROS


def imprimir(sol: dict) -> None:

    W = 58  # ancho del panel

    def linea(char="─"):
        return char * W

    def fila(label, valor, color=""):
        pad = W - 2 - len(label) - len(valor)
        return f"  {label}{' ' * pad}{valor}"

    print()
    print("╔" + "═" * W + "╗")
    print("║" + " RED DE DISTRIBUCIÓN — SOLUCIÓN ÓPTIMA".center(W) + "║")
    print("╚" + "═" * W + "╝")

    if not sol["factible"]:
        print(f"\n  Estado: {sol['estado']} — sin solución factible.\n")
        return

    # ── Estado y costo ────────────────────────────────────────────────────────
    print()
    print(f"  Estado   : {sol['estado']}")
    print(f"  {'─'*54}")
    costo_str = f"$ {sol['costo_total']:>10,.2f}"
    print(f"  {'COSTO TOTAL MÍNIMO':<34}{costo_str:>20}")
    print(f"  {'─'*54}")

    d = sol["desglose"]
    items_costo = [
        ("    Costos fijos apertura CDs",  d["costos_fijos"]),
        ("    Transporte directo P→C",      d["transporte_directo"]),
        ("    Transporte P→CD",             d["transporte_planta_cd"]),
        ("    Transporte CD→C",             d["transporte_cd_cliente"]),
        ("    Penalizaciones por déficit",  d["penalizaciones"]),
    ]
    for label, val in items_costo:
        if val > 0:
            print(f"  {label:<36}$ {val:>10,.2f}")

    # ── Centros ───────────────────────────────────────────────────────────────
    print()
    print(f"  {linea()}")
    print(f"  {'CENTROS DE DISTRIBUCIÓN':^{W-2}}")
    print(f"  {linea()}")
    centros_map = {c.id: c for c in CENTROS}
    for d_id in [c.id for c in CENTROS]:
        estado = "ABIERTO ✓" if d_id in sol["centros_abiertos"] else "cerrado  ✗"
        c = centros_map[d_id]
        print(f"  {d_id}   Cap: {c.capacidad:.0f} u.   Fijo: ${c.costo_fijo:,.0f}   [{estado}]")

    if not sol["centros_abiertos"]:
        print(f"\n  → Ningún CD abierto: costos fijos no compensan el ahorro")

    # ── Rutas y flujos ────────────────────────────────────────────────────────
    n_dir = len(sol["rutas_directas"])
    n_cd  = len(sol["rutas_cd"])
    total = n_dir + n_cd

    print()
    print(f"  {linea()}")
    print(f"  RUTAS ACTIVAS: {total} / 8 máximo   ({n_dir} directas, {n_cd} vía CD)")
    print(f"  {linea()}")

    if sol["flujo_directo"]:
        print(f"  Flujos directos Planta → Cliente:")
        # Agrupar por planta para legibilidad
        por_planta = {}
        for (p, c), v in sorted(sol["flujo_directo"].items()):
            por_planta.setdefault(p, []).append((c, v))
        for p, envios in sorted(por_planta.items()):
            oferta = {pl.id: pl.oferta for pl in PLANTAS}[p]
            total_enviado = sum(v for _, v in envios)
            destinos = "  +  ".join(f"{c}: {v:.0f} u." for c, v in envios)
            print(f"    {p} (oferta {oferta:.0f})  →  {destinos}")
            print(f"    {'':>4}Total enviado: {total_enviado:.0f} u."
                  f"  |  Sin usar: {oferta - total_enviado:.0f} u.")
            print()

    if sol["flujo_planta_cd"]:
        print(f"  Flujos Planta → Centro de distribución:")
        for (p, d), v in sorted(sol["flujo_planta_cd"].items()):
            print(f"    {p} → {d} : {v:.0f} u.")
        print()

    if sol["flujo_cd_cliente"]:
        print(f"  Flujos Centro → Cliente:")
        for (d, c), v in sorted(sol["flujo_cd_cliente"].items()):
            print(f"    {d} → {c} : {v:.0f} u.")
        print()

    # ── Demanda por cliente ───────────────────────────────────────────────────
    print(f"  {linea()}")
    print(f"  SATISFACCIÓN DE DEMANDA")
    print(f"  {linea()}")
    print(f"  {'Cliente':<10}{'Demanda':>10}{'Recibido':>12}{'Déficit':>12}{'Cobertura':>12}")
    print(f"  {'─'*8:<10}{'─'*7:>10}{'─'*8:>12}{'─'*8:>12}{'─'*9:>12}")

    clientes_map = {c.id: c for c in CLIENTES}
    deficit_map  = sol.get("deficit", {})

    for c_id in [c.id for c in CLIENTES]:
        dem  = clientes_map[c_id].demanda
        def_ = deficit_map.get(c_id, 0)
        rec  = dem - def_
        pct  = 100 * rec / dem
        flag = " ◄ DÉFICIT" if def_ > 0 else ""
        print(f"  {c_id:<10}{dem:>10.0f}{rec:>12.0f}{def_:>12.0f}{pct:>11.0f}%{flag}")

    # ── Resumen déficit ───────────────────────────────────────────────────────
    if deficit_map:
        print()
        print(f"  {linea('─')}")
        total_def  = sum(deficit_map.values())
        total_pen  = sum(clientes_map[c].penalizacion * v
                         for c, v in deficit_map.items())
        print(f"  Déficit total: {total_def:.0f} u.   "
              f"Penalización total: ${total_pen:,.2f}")
        print(f"  Decisión: sacrificar demanda de menor penalización")
        for c_id, v in sorted(deficit_map.items(),
                               key=lambda x: clientes_map[x[0]].penalizacion):
            pen = clientes_map[c_id].penalizacion
            print(f"    {c_id}: {v:.0f} u. × ${pen}/u. = ${v*pen:,.2f}")
    else:
        print(f"\n  Demanda satisfecha al 100 %.")

    print()
    print("╔" + "═" * W + "╗")
    print("║" + " FIN DEL REPORTE ".center(W) + "║")
    print("╚" + "═" * W + "╝")
    print()
    