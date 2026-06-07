from data import PLANTAS, CLIENTES, CENTROS


def imprimir(sol: dict) -> None:
    sep  = "─" * 54
    sep2 = "═" * 54

    print(f"\n{sep2}")
    print("  RED DE DISTRIBUCIÓN — SOLUCIÓN ÓPTIMA")
    print(sep2)

    if not sol["factible"]:
        print(f"  Estado: {sol['estado']} — no se encontró solución factible.")
        return

    print(f"  Estado  : {sol['estado']}")
    print(f"  Costo total mínimo: $ {sol['costo_total']:,.2f}")
    print(f"\n  Desglose de costos:")
    d = sol["desglose"]
    print(f"    Costos fijos apertura  : $ {d['costos_fijos']:>8,.2f}")
    print(f"    Transporte Planta→CD   : $ {d['transporte_planta_cd']:>8,.2f}")
    print(f"    Transporte CD→Cliente  : $ {d['transporte_cd_cliente']:>8,.2f}")
    print(f"    Penalizaciones déficit : $ {d['penalizaciones']:>8,.2f}")

    print(f"\n{sep}")
    print("  Centros de distribución abiertos:")
    centros = {c.id: c for c in CENTROS}
    for cid in sol["centros_abiertos"]:
        c = centros[cid]
        print(f"    {cid}  (cap={c.capacidad}, fijo=${c.costo_fijo})")

    print(f"\n{sep}")
    print("  Flujos Planta → Centro de distribución:")
    for (p, d), v in sorted(sol["flujo_planta_cd"].items()):
        print(f"    {p} → {d} : {v:>7.1f} unidades")

    print(f"\n{sep}")
    print("  Flujos Centro de distribución → Cliente:")
    for (d, c), v in sorted(sol["flujo_cd_cliente"].items()):
        print(f"    {d} → {c} : {v:>7.1f} unidades")

    print(f"\n{sep}")
    print(f"  Rutas activas ({len(sol['rutas_activas'])} / máx 8):")
    for d, c in sorted(sol["rutas_activas"]):
        print(f"    {d} → {c}")

    if sol["deficit"]:
        print(f"\n{sep}")
        print("  Demanda no satisfecha (déficit):")
        clientes = {c.id: c for c in CLIENTES}
        for cid, v in sorted(sol["deficit"].items()):
            pen = clientes[cid].penalizacion
            print(f"    {cid}: {v:.1f} unidades  (penalización ${pen}/u → ${v*pen:,.2f})")
    else:
        print(f"\n  Demanda satisfecha al 100 %.")

    print(f"{sep2}\n")
    