"""
Modelo MILP con rutas directas Y opción de pasar por CD.

El solver elige libremente entre:
  - Ruta directa : Planta p  →  Cliente c
  - Ruta vía CD  : Planta p  →  Centro d  →  Cliente c

Variables:
    f[p,c]   continua ≥ 0   flujo directo planta p → cliente c
    x[p,d]   continua ≥ 0   flujo planta p → centro d
    y[d,c]   continua ≥ 0   flujo centro d → cliente c
    z[d]     binaria         1 si el centro d se abre
    u[p,c]   binaria         1 si la ruta directa p→c está activa
    w[d,c]   binaria         1 si la ruta CD d→c está activa
    s[c]     continua ≥ 0   demanda no satisfecha del cliente c

Función objetivo (minimizar):
    costos_fijos_CD
    + transporte directo P→C
    + transporte P→CD  +  transporte CD→C
    + penalizaciones por déficit

Restricciones:
    1.  Oferta de cada planta  (directo + vía CD)
    2.  Balance en cada CD  (entrada = salida)
    3.  Capacidad de cada CD  (solo si está abierto)
    4.  Satisfacción de demanda  (directo + vía CD + déficit)
    5.  Linking ruta directa  u[p,c] ↔ f[p,c]
    6.  Linking ruta CD       w[d,c] ↔ y[d,c]
    7.  Máximo 8 rutas activas  (directas + CD→C)
"""

from pulp import LpProblem, LpMinimize, LpVariable, LpBinary, lpSum
from data import (
    PLANTAS, CLIENTES, CENTROS,
    COSTO_PLANTA_CLIENTE, COSTO_PLANTA_CD, COSTO_CD_CLIENTE,
    MAX_RUTAS_ACTIVAS,
)


def construir_modelo():
    prob = LpProblem("Red_Distribucion_Logistica", LpMinimize)

    P = [p.id for p in PLANTAS]
    C = [c.id for c in CLIENTES]
    D = [d.id for d in CENTROS]

    oferta     = {p.id: p.oferta       for p in PLANTAS}
    demanda    = {c.id: c.demanda      for c in CLIENTES}
    penal      = {c.id: c.penalizacion for c in CLIENTES}
    capacidad  = {d.id: d.capacidad    for d in CENTROS}
    costo_fijo = {d.id: d.costo_fijo   for d in CENTROS}

    # ── Variables ──────────────────────────────────────────────────────────────

    # Rutas directas
    f = {(p, c): LpVariable(f"f_{p}_{c}", lowBound=0) for p in P for c in C}
    u = {(p, c): LpVariable(f"u_{p}_{c}", cat=LpBinary) for p in P for c in C}

    # Rutas vía CD
    x = {(p, d): LpVariable(f"x_{p}_{d}", lowBound=0) for p in P for d in D}
    y = {(d, c): LpVariable(f"y_{d}_{c}", lowBound=0) for d in D for c in C}
    z = {d:      LpVariable(f"z_{d}",      cat=LpBinary) for d in D}
    w = {(d, c): LpVariable(f"w_{d}_{c}", cat=LpBinary) for d in D for c in C}

    # Déficit
    s = {c: LpVariable(f"s_{c}", lowBound=0) for c in C}

    # ── Función objetivo ───────────────────────────────────────────────────────
    prob += (
        lpSum(costo_fijo[d] * z[d] for d in D)
        + lpSum(COSTO_PLANTA_CLIENTE[(p, c)] * f[(p, c)] for p in P for c in C)
        + lpSum(COSTO_PLANTA_CD[(p, d)]      * x[(p, d)] for p in P for d in D)
        + lpSum(COSTO_CD_CLIENTE[(d, c)]     * y[(d, c)] for d in D for c in C)
        + lpSum(penal[c] * s[c] for c in C)
    ), "Costo_Total"

    # ── Restricciones ──────────────────────────────────────────────────────────

    # 1. Oferta: lo que sale directo + lo que va a CDs ≤ oferta
    for p in P:
        prob += (
            lpSum(f[(p, c)] for c in C) + lpSum(x[(p, d)] for d in D) <= oferta[p],
            f"Oferta_{p}"
        )

    # 2. Balance en cada CD
    for d in D:
        prob += (
            lpSum(x[(p, d)] for p in P) == lpSum(y[(d, c)] for c in C),
            f"Balance_{d}"
        )

    # 3. Capacidad del CD (solo si está abierto)
    for d in D:
        prob += (
            lpSum(x[(p, d)] for p in P) <= capacidad[d] * z[d],
            f"Capacidad_{d}"
        )

    # 4. Satisfacción de demanda
    for c in C:
        prob += (
            lpSum(f[(p, c)] for p in P)
            + lpSum(y[(d, c)] for d in D)
            + s[c] >= demanda[c],
            f"Demanda_{c}"
        )

    # 5. Linking ruta directa
    M = max(c.demanda for c in CLIENTES)
    for p in P:
        for c in C:
            prob += f[(p, c)] <= M * u[(p, c)], f"LinkDir_{p}_{c}"

    # 6. Linking ruta vía CD
    for d in D:
        for c in C:
            prob += y[(d, c)] <= M * w[(d, c)], f"LinkCD_{d}_{c}"

    # 7. Máximo de rutas activas (directas + CD→C)
    prob += (
        lpSum(u[(p, c)] for p in P for c in C)
        + lpSum(w[(d, c)] for d in D for c in C) <= MAX_RUTAS_ACTIVAS,
        "Max_Rutas"
    )

    return prob, f, x, y, z, u, w, s
