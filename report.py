from data import PLANTAS, CLIENTES, CENTROS


def imprimir(sol: dict) -> None:
    sep  = "─" * 56
    sep2 = "═" * 56

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
    print(f"    Costos fijos CD abiertos   : $ {d['costos_fijos']:>8,.2f}")
    print(f"    Transporte directo P→C     : $ {d['transporte_directo']:>8,.2f}")
    print(f"    Transporte P→CD            : $ {d['transporte_planta_cd']:>8,.2f}")
    print(f"    Transporte CD→C            : $ {d['transporte_cd_cliente']:>8,.2f}")
    print(f"    Penalizaciones déficit     : $ {d['penalizaciones']:>8,.2f}")

    print(f"\n{sep}")
    if sol["centros_abiertos"]:
        print("  Centros de distribución abiertos:")
        centros = {c.id: c for c in CENTROS}
        for cid in sol["centros_abiertos"]:
            c = centros[cid]
            print(f"    {cid}  (cap={c.capacidad}, fijo=${c.costo_fijo})")
    else:
        print("  Centros de distribución: ninguno abierto")
        print("  (los costos fijos superan el ahorro en transporte)")

    n_dir = len(sol["rutas_directas"])
    n_cd  = len(sol["rutas_cd"])
    total_rutas = n_dir + n_cd

    print(f"\n{sep}")
    print(f"  Rutas activas: {total_rutas} / máx 8  ({n_dir} directas, {n_cd} vía CD)")

    if sol["flujo_directo"]:
        print(f"\n  Flujos directos Planta → Cliente:")
        for (p, c), v in sorted(sol["flujo_directo"].items()):
            print(f"    {p} → {c} : {v:>7.1f} unidades")

    if sol["flujo_planta_cd"]:
        print(f"\n  Flujos Planta → Centro de distribución:")
        for (p, d), v in sorted(sol["flujo_planta_cd"].items()):
            print(f"    {p} → {d} : {v:>7.1f} unidades")

    if sol["flujo_cd_cliente"]:
        print(f"\n  Flujos Centro de distribución → Cliente:")
        for (d, c), v in sorted(sol["flujo_cd_cliente"].items()):
            print(f"    {d} → {c} : {v:>7.1f} unidades")

    if sol["deficit"]:
        print(f"\n{sep}")
        print("  Demanda no satisfecha (déficit):")
        clientes = {c.id: c for c in CLIENTES}
        for cid, v in sorted(sol["deficit"].items()):
            pen = clientes[cid].penalizacion
            print(f"    {cid}: {v:.1f} unidades  (${pen}/u → ${v*pen:,.2f})")
    else:
        print(f"\n  Demanda satisfecha al 100 %.")

    print(f"{sep2}\n")
    