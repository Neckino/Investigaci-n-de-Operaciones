"""
model.py — Construcción del modelo MILP para OptiNet.

Formulación matemática
──────────────────────
Conjuntos
  P   plantas
  D   centros de distribución (CDs)
  C   clientes
  A   arcos  (origen, destino, tipo)

Variables de decisión
  x[a]   ≥ 0,  continua  — flujo en el arco a
  y[d]   ∈ {0,1}         — apertura del CD d
  z[a]   ∈ {0,1}         — ruta activa (flujo > 0) en el arco a
  s[c]   ≥ 0,  continua  — déficit del cliente c (unidades no satisfechas)

Función objetivo  (minimizar)
  Σ_a  unit_cost[a] · x[a]
  + Σ_d  fixed_cost[d] · y[d]
  + Σ_c  penalty[c]  · s[c]

Restricciones
  [R1] Oferta máxima por planta:
       Σ_{a: origen=p} x[a]  ≤  supply[p]          ∀ p ∈ P

  [R2] Satisfacción de demanda (con déficit permitido):
       Σ_{a: destino=c} x[a] + s[c]  ≥  demand[c]  ∀ c ∈ C

  [R3] Flujo de CD acotado por apertura y capacidad:
       Σ_{a: destino=d} x[a]  ≤  capacity[d] · y[d]  ∀ d ∈ D
       (si un CD está cerrado, no puede recibir ni enviar flujo)

  [R4] Conservación en CDs (entrada = salida):
       Σ_{a: destino=d} x[a]  =  Σ_{a: origen=d} x[a]  ∀ d ∈ D

  [R5] Activación de ruta (Big-M):
       x[a]  ≤  M · z[a]                            ∀ a ∈ A

  [R6] Límite global de rutas activas:
       Σ_a z[a]  ≤  max_active_routes

  [R7] Capacidad de arco (si se especifica):
       x[a]  ≤  capacity[a]                          ∀ a con capacity definida
"""

from __future__ import annotations

import pulp
from dataclasses import dataclass, field
from typing import Optional

from .data import NetworkData, Arc


# ─────────────────────────────────────────────
# Contenedor del modelo construido
# ─────────────────────────────────────────────

@dataclass
class MILPModel:
    """
    Encapsula el problema PuLP y las referencias a sus variables,
    para que solver.py pueda resolverlo y extraer resultados fácilmente.
    """
    problem: pulp.LpProblem

    # Variables indexadas por arc.id
    x: dict[str, pulp.LpVariable] = field(default_factory=dict)  # flujo continuo
    z: dict[str, pulp.LpVariable] = field(default_factory=dict)  # ruta activa (binaria)

    # Variables indexadas por dist_center.id
    y: dict[str, pulp.LpVariable] = field(default_factory=dict)  # apertura CD (binaria)

    # Variables indexadas por client.id
    s: dict[str, pulp.LpVariable] = field(default_factory=dict)  # déficit

    # Referencia al dato de red (útil en solver para interpretar resultados)
    network: Optional[NetworkData] = None


# ─────────────────────────────────────────────
# Constructor del modelo
# ─────────────────────────────────────────────

def build_model(net: NetworkData, name: str = "OptiNet_MILP") -> MILPModel:
    """
    Traduce un NetworkData a un LpProblem listo para resolver.

    Parameters
    ----------
    net  : NetworkData validado (llamar net.validate() antes si es necesario)
    name : nombre del problema en PuLP

    Returns
    -------
    MILPModel con problem y todas las variables referenciadas.
    """
    prob = pulp.LpProblem(name, pulp.LpMinimize)
    M    = net.config.big_m

    # ── 1. Variables ────────────────────────────────────────────────────

    # Flujo continuo en cada arco
    x: dict[str, pulp.LpVariable] = {
        arc.id: pulp.LpVariable(
            f"x_{arc.id}",
            lowBound=0,
            upBound=arc.capacity,           # None → sin cota superior explícita
            cat=pulp.LpContinuous,
        )
        for arc in net.arcs
    }

    # Binaria: ruta activa
    z: dict[str, pulp.LpVariable] = {
        arc.id: pulp.LpVariable(f"z_{arc.id}", cat=pulp.LpBinary)
        for arc in net.arcs
    }

    # Binaria: apertura de CD
    y: dict[str, pulp.LpVariable] = {
        dc.id: pulp.LpVariable(f"y_{dc.id}", cat=pulp.LpBinary)
        for dc in net.dist_centers
    }

    # Déficit por cliente
    s: dict[str, pulp.LpVariable] = {
        client.id: pulp.LpVariable(
            f"s_{client.id}",
            lowBound=0,
            upBound=client.demand if net.config.allow_partial_supply else 0,
            cat=pulp.LpContinuous,
        )
        for client in net.clients
    }

    # ── 2. Función objetivo ─────────────────────────────────────────────

    transport_cost = pulp.lpSum(arc.unit_cost * x[arc.id] for arc in net.arcs)

    fixed_cost = pulp.lpSum(
        dc.fixed_cost * y[dc.id] for dc in net.dist_centers
    )

    penalty_cost = pulp.lpSum(
        client.penalty * s[client.id] for client in net.clients
    )

    prob += transport_cost + fixed_cost + penalty_cost, "Costo_Total"

    # ── 3. Restricciones ────────────────────────────────────────────────

    # [R1] Oferta máxima por planta
    for plant in net.plants:
        salida = [arc for arc in net.arcs if arc.origin_id == plant.id]
        if salida:
            prob += (
                pulp.lpSum(x[a.id] for a in salida) <= plant.supply,
                f"R1_oferta_{plant.id}",
            )

    # [R2] Satisfacción de demanda con posible déficit
    for client in net.clients:
        entrada = [arc for arc in net.arcs if arc.dest_id == client.id]
        prob += (
            pulp.lpSum(x[a.id] for a in entrada) + s[client.id] >= client.demand,
            f"R2_demanda_{client.id}",
        )

    # [R3] Capacidad de CD condicionada a apertura
    for dc in net.dist_centers:
        entrada_dc = [arc for arc in net.arcs if arc.dest_id == dc.id]
        if entrada_dc:
            prob += (
                pulp.lpSum(x[a.id] for a in entrada_dc) <= dc.capacity * y[dc.id],
                f"R3_cap_cd_{dc.id}",
            )

    # [R4] Conservación de flujo en CDs
    for dc in net.dist_centers:
        entrada_dc = [arc for arc in net.arcs if arc.dest_id == dc.id]
        salida_dc  = [arc for arc in net.arcs if arc.origin_id == dc.id]
        if entrada_dc and salida_dc:
            prob += (
                pulp.lpSum(x[a.id] for a in entrada_dc)
                == pulp.lpSum(x[a.id] for a in salida_dc),
                f"R4_conservacion_{dc.id}",
            )

    # [R5] Big-M: activación de ruta
    for arc in net.arcs:
        ub = arc.capacity if arc.capacity is not None else M
        prob += (x[arc.id] <= ub * z[arc.id], f"R5_bigm_{arc.id}")

    # [R6] Límite global de rutas activas
    prob += (
        pulp.lpSum(z[arc.id] for arc in net.arcs) <= net.config.max_active_routes,
        "R6_max_rutas",
    )

    # [R7] Capacidad explícita de arco (ya manejada en upBound, se deja como
    # restricción explícita para visibilidad en el reporte del modelo)
    for arc in net.arcs:
        if arc.capacity is not None:
            prob += (x[arc.id] <= arc.capacity, f"R7_cap_arco_{arc.id}")

    return MILPModel(
        problem=prob,
        x=x,
        z=z,
        y=y,
        s=s,
        network=net,
    )
    