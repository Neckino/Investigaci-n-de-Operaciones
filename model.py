"""
Modelo MILP de dos escalones: Planta → Centro de Distribución → Cliente

Variables:
    x[p,d]   continua ≥ 0   flujo de planta p a centro d
    y[d,c]   continua ≥ 0   flujo de centro d a cliente c
    z[d]     binaria         1 si el centro d se abre
    w[d,c]   binaria         1 si la ruta d→c está activa
    s[c]     continua ≥ 0   demanda no satisfecha del cliente c

Función objetivo (minimizar):
    costos_fijos + costos_transporte_P_CD + costos_transporte_CD_C + penalizaciones

Restricciones:
    1. Oferta de cada planta
    2. Balance en cada centro (lo que entra = lo que sale)
    3. Capacidad de cada centro (solo si está abierto)
    4. Satisfacción de demanda (con posible déficit)
    5. Linking ruta activa ↔ flujo positivo
    6. Máximo 8 rutas CD→cliente activas
    7. Dominios de variables
"""

from pulp import (
    LpProblem, LpMinimize, LpVariable, LpBinary, lpSum, value
)
from data import (
    PLANTAS, CLIENTES, CENTROS,
    COSTO_PLANTA_CD, COSTO_CD_CLIENTE,
    MAX_RUTAS_ACTIVAS,
)


def construir_modelo() -> LpProblem:
    prob = LpProblem("Red_Distribucion_Logistica", LpMinimize)

    P = [p.id for p in PLANTAS]
    C = [c.id for c in CLIENTES]
    D = [d.id for d in CENTROS]

    oferta      = {p.id: p.oferta      for p in PLANTAS}
    demanda     = {c.id: c.demanda     for c in CLIENTES}
    penal       = {c.id: c.penalizacion for c in CLIENTES}
    capacidad   = {d.id: d.capacidad   for d in CENTROS}
    costo_fijo  = {d.id: d.costo_fijo  for d in CENTROS}

    # ── Variables ──────────────────────────────────────────────────────────────
    x = {(p, d): LpVariable(f"x_{p}_{d}", lowBound=0)
         for p in P for d in D}

    y = {(d, c): LpVariable(f"y_{d}_{c}", lowBound=0)
         for d in D for c in C}

    z = {d: LpVariable(f"z_{d}", cat=LpBinary) for d in D}

    w = {(d, c): LpVariable(f"w_{d}_{c}", cat=LpBinary)
         for d in D for c in C}

    s = {c: LpVariable(f"s_{c}", lowBound=0) for c in C}

    # ── Función objetivo ───────────────────────────────────────────────────────
    prob += (
        lpSum(costo_fijo[d] * z[d] for d in D)
        + lpSum(COSTO_PLANTA_CD[(p, d)] * x[(p, d)] for p in P for d in D)
        + lpSum(COSTO_CD_CLIENTE[(d, c)] * y[(d, c)] for d in D for c in C)
        + lpSum(penal[c] * s[c] for c in C)
    ), "Costo_Total"

    # ── Restricciones ──────────────────────────────────────────────────────────

    # 1. Oferta de cada planta
    for p in P:
        prob += lpSum(x[(p, d)] for d in D) <= oferta[p], f"Oferta_{p}"

    # 2. Balance en cada centro
    for d in D:
        prob += (
            lpSum(x[(p, d)] for p in P) == lpSum(y[(d, c)] for c in C),
            f"Balance_{d}"
        )

    # 3. Capacidad del centro (solo si está abierto)
    for d in D:
        prob += (
            lpSum(x[(p, d)] for p in P) <= capacidad[d] * z[d],
            f"Capacidad_{d}"
        )

    # 4. Satisfacción de demanda con posible déficit
    for c in C:
        prob += (
            lpSum(y[(d, c)] for d in D) + s[c] >= demanda[c],
            f"Demanda_{c}"
        )

    # 5. Linking: flujo y[d,c] > 0 solo si ruta w[d,c] = 1
    M = max(c.demanda for c in CLIENTES)
    for d in D:
        for c in C:
            prob += y[(d, c)] <= M * w[(d, c)], f"Linking_{d}_{c}"

    # 6. Máximo de rutas activas
    prob += (
        lpSum(w[(d, c)] for d in D for c in C) <= MAX_RUTAS_ACTIVAS,
        "Max_Rutas"
    )

    return prob, x, y, z, w, s
