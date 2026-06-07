from pulp import LpStatus, value, PULP_CBC_CMD
from model import construir_modelo
from data import PLANTAS, CLIENTES, CENTROS, COSTO_PLANTA_CLIENTE, COSTO_PLANTA_CD, COSTO_CD_CLIENTE


def resolver() -> dict:
    prob, f, x, y, z, u, w, s = construir_modelo()

    P = [p.id for p in PLANTAS]
    C = [c.id for c in CLIENTES]
    D = [d.id for d in CENTROS]

    costo_fijo = {d.id: d.costo_fijo   for d in CENTROS}
    penal      = {c.id: c.penalizacion for c in CLIENTES}

    prob.solve(PULP_CBC_CMD(msg=0))

    estado = LpStatus[prob.status]
    if estado not in ("Optimal", "Feasible"):
        return {"estado": estado, "factible": False}

    # ── Extraer flujos ─────────────────────────────────────────────────────────
    flujo_directo = {
        (p, c): round(value(f[(p, c)]), 4)
        for p in P for c in C if value(f[(p, c)]) > 1e-6
    }
    flujo_planta_cd = {
        (p, d): round(value(x[(p, d)]), 4)
        for p in P for d in D if value(x[(p, d)]) > 1e-6
    }
    flujo_cd_cliente = {
        (d, c): round(value(y[(d, c)]), 4)
        for d in D for c in C if value(y[(d, c)]) > 1e-6
    }

    centros_abiertos = [d for d in D if value(z[d]) > 0.5]

    rutas_directas = [(p, c) for p in P for c in C if value(u[(p, c)]) > 0.5]
    rutas_cd       = [(d, c) for d in D for c in C if value(w[(d, c)]) > 0.5]

    deficit = {
        c: round(value(s[c]), 4)
        for c in C if value(s[c]) > 1e-6
    }

    # ── Desglose de costos ─────────────────────────────────────────────────────
    costo_fijos_total    = sum(costo_fijo[d] for d in centros_abiertos)
    costo_transp_directo = sum(COSTO_PLANTA_CLIENTE[(p, c)] * v for (p, c), v in flujo_directo.items())
    costo_transp_pcd     = sum(COSTO_PLANTA_CD[(p, d)]      * v for (p, d), v in flujo_planta_cd.items())
    costo_transp_cdc     = sum(COSTO_CD_CLIENTE[(d, c)]     * v for (d, c), v in flujo_cd_cliente.items())
    costo_penalizacion   = sum(penal[c] * v for c, v in deficit.items())

    return {
        "estado":           estado,
        "factible":         True,
        "costo_total":      round(value(prob.objective), 2),
        "desglose": {
            "costos_fijos":          round(costo_fijos_total, 2),
            "transporte_directo":    round(costo_transp_directo, 2),
            "transporte_planta_cd":  round(costo_transp_pcd, 2),
            "transporte_cd_cliente": round(costo_transp_cdc, 2),
            "penalizaciones":        round(costo_penalizacion, 2),
        },
        "centros_abiertos":  centros_abiertos,
        "rutas_directas":    rutas_directas,
        "rutas_cd":          rutas_cd,
        "flujo_directo":     flujo_directo,
        "flujo_planta_cd":   flujo_planta_cd,
        "flujo_cd_cliente":  flujo_cd_cliente,
        "deficit":           deficit,
    }
    