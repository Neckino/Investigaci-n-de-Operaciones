"""
solver.py — Resolución del modelo MILP y extracción de resultados para OptiNet.

Flujo típico:
    net    = NetworkData(...)
    milp   = build_model(net)
    result = solve(milp)
    # result.status, result.total_cost, result.flows, ...
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import pulp

from .data import NetworkData
from .model import MILPModel, build_model


# ─────────────────────────────────────────────
# Estructuras de resultado
# ─────────────────────────────────────────────

@dataclass
class ArcFlow:
    """Flujo asignado a un arco en la solución óptima."""
    arc_id: str
    origin_id: str
    origin_type: str
    dest_id: str
    dest_type: str
    flow: float
    unit_cost: float
    total_cost: float
    active: bool          # z[arc] == 1


@dataclass
class DCDecision:
    """Decisión de apertura para un centro de distribución."""
    dc_id: str
    name: str
    opened: bool
    fixed_cost_incurred: float
    throughput: float     # flujo total que pasó por el CD


@dataclass
class ClientResult:
    """Resultado de atención para un cliente."""
    client_id: str
    name: str
    demand: float
    received: float
    deficit: float
    penalty_per_unit: float
    penalty_cost: float
    fill_rate: float      # received / demand  (0–1)


@dataclass
class SolverResult:
    """
    Resultado completo de una ejecución del solver.

    Todos los campos de costo están expresados en las mismas unidades
    monetarias que se definieron en NetworkData.
    """
    # Estado general
    status: str                          # "Optimal", "Infeasible", "Unbounded", ...
    solver_name: str
    solve_time_sec: float

    # Costos desglosados
    transport_cost: float = 0.0
    fixed_cost: float     = 0.0
    penalty_cost: float   = 0.0
    total_cost: float     = 0.0

    # Detalle por entidad
    arc_flows: list[ArcFlow]       = field(default_factory=list)
    dc_decisions: list[DCDecision] = field(default_factory=list)
    client_results: list[ClientResult] = field(default_factory=list)

    # Métricas de red
    active_routes: int   = 0
    supply_used: float   = 0.0
    total_supply: float  = 0.0
    total_demand: float  = 0.0
    total_deficit: float = 0.0

    # Mensaje de error si status != Optimal
    error_message: Optional[str] = None

    @property
    def feasible(self) -> bool:
        return self.status == "Optimal"

    @property
    def service_level(self) -> float:
        """Fracción de la demanda total que fue satisfecha."""
        if self.total_demand == 0:
            return 1.0
        return max(0.0, (self.total_demand - self.total_deficit) / self.total_demand)


# ─────────────────────────────────────────────
# Función principal
# ─────────────────────────────────────────────

def solve(
    milp: MILPModel,
    solver_name: str = "CBC",
    time_limit_sec: int = 120,
    gap_rel: float = 0.0,           # 0 = óptimo exacto; >0 permite gap relativo
    msg: bool = False,              # True = imprime log del solver
) -> SolverResult:
    """
    Resuelve el MILPModel y retorna un SolverResult con todo el detalle.

    Parameters
    ----------
    milp           : modelo construido con build_model()
    solver_name    : "CBC" (default, incluido en PuLP) | "GLPK" | "CPLEX" | "GUROBI"
    time_limit_sec : tiempo máximo de resolución
    gap_rel        : tolerancia de gap relativo (0 = exacto)
    msg            : mostrar log del solver en stdout

    Returns
    -------
    SolverResult
    """
    net = milp.network
    assert net is not None, "MILPModel.network no puede ser None al resolver."

    # ── Selección de solver ──────────────────────────────────────────────
    solver = _get_solver(solver_name, time_limit_sec, gap_rel, msg)

    # ── Resolución ───────────────────────────────────────────────────────
    t0 = time.perf_counter()
    milp.problem.solve(solver)
    elapsed = time.perf_counter() - t0

    status_str = pulp.LpStatus[milp.problem.status]

    if status_str not in ("Optimal", "Not Solved"):
        # Infeasible / Unbounded — retornamos resultado mínimo
        return SolverResult(
            status=status_str,
            solver_name=solver_name,
            solve_time_sec=elapsed,
            total_demand=net.total_demand,
            total_supply=net.total_supply,
            error_message=f"Solver terminó con estado: {status_str}",
        )

    # ── Extracción de resultados ─────────────────────────────────────────

    # Flujos por arco
    arc_flows: list[ArcFlow] = []
    transport_cost = 0.0

    for arc in net.arcs:
        flow_val  = pulp.value(milp.x[arc.id]) or 0.0
        active_val = round(pulp.value(milp.z[arc.id]) or 0.0)
        cost_val  = flow_val * arc.unit_cost
        transport_cost += cost_val

        arc_flows.append(ArcFlow(
            arc_id=arc.id,
            origin_id=arc.origin_id,
            origin_type=arc.origin_type,
            dest_id=arc.dest_id,
            dest_type=arc.dest_type,
            flow=round(flow_val, 4),
            unit_cost=arc.unit_cost,
            total_cost=round(cost_val, 4),
            active=bool(active_val),
        ))

    # Decisiones de CDs
    dc_decisions: list[DCDecision] = []
    fixed_cost = 0.0

    for dc in net.dist_centers:
        opened = bool(round(pulp.value(milp.y[dc.id]) or 0.0))
        fc     = dc.fixed_cost if opened else 0.0
        fixed_cost += fc

        # throughput = suma de flujos entrantes al CD
        throughput = sum(
            pulp.value(milp.x[a.id]) or 0.0
            for a in net.arcs if a.dest_id == dc.id
        )

        dc_decisions.append(DCDecision(
            dc_id=dc.id,
            name=dc.name,
            opened=opened,
            fixed_cost_incurred=fc,
            throughput=round(throughput, 4),
        ))

    # Resultados por cliente
    client_results: list[ClientResult] = []
    penalty_cost = 0.0

    for client in net.clients:
        deficit_val  = pulp.value(milp.s[client.id]) or 0.0
        received_val = client.demand - deficit_val
        pen_cost     = client.penalty * deficit_val
        penalty_cost += pen_cost
        fill_rate    = received_val / client.demand if client.demand > 0 else 1.0

        client_results.append(ClientResult(
            client_id=client.id,
            name=client.name,
            demand=client.demand,
            received=round(max(0.0, received_val), 4),
            deficit=round(max(0.0, deficit_val), 4),
            penalty_per_unit=client.penalty,
            penalty_cost=round(pen_cost, 4),
            fill_rate=round(min(1.0, max(0.0, fill_rate)), 4),
        ))

    active_routes = sum(1 for af in arc_flows if af.active)
    supply_used   = sum(af.flow for af in arc_flows if af.origin_type == "plant")
    total_deficit = sum(cr.deficit for cr in client_results)
    total_cost    = transport_cost + fixed_cost + penalty_cost

    return SolverResult(
        status=status_str,
        solver_name=solver_name,
        solve_time_sec=round(elapsed, 4),
        transport_cost=round(transport_cost, 4),
        fixed_cost=round(fixed_cost, 4),
        penalty_cost=round(penalty_cost, 4),
        total_cost=round(total_cost, 4),
        arc_flows=arc_flows,
        dc_decisions=dc_decisions,
        client_results=client_results,
        active_routes=active_routes,
        supply_used=round(supply_used, 4),
        total_supply=net.total_supply,
        total_demand=net.total_demand,
        total_deficit=round(total_deficit, 4),
    )


# ─────────────────────────────────────────────
# Función de alto nivel (build + solve en uno)
# ─────────────────────────────────────────────

def optimize(
    net: NetworkData,
    solver_name: str = "CBC",
    time_limit_sec: int = 120,
    gap_rel: float = 0.0,
    msg: bool = False,
) -> SolverResult:
    """
    Atajo conveniente: valida, construye y resuelve en una sola llamada.

    >>> result = optimize(net)
    >>> print(result.total_cost, result.service_level)
    """
    issues = net.validate()
    if any("duplicados" in i or "no existe" in i for i in issues):
        return SolverResult(
            status="Invalid",
            solver_name=solver_name,
            solve_time_sec=0.0,
            error_message="Red inválida: " + "; ".join(issues),
        )

    milp = build_model(net)
    return solve(milp, solver_name=solver_name,
                 time_limit_sec=time_limit_sec, gap_rel=gap_rel, msg=msg)


# ─────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────

def _get_solver(
    name: str,
    time_limit: int,
    gap_rel: float,
    msg: bool,
) -> pulp.LpSolver:
    """Instancia el solver de PuLP con los parámetros dados."""
    name = name.upper()
    opts: dict = dict(msg=msg, timeLimit=time_limit)

    if name == "CBC":
        return pulp.PULP_CBC_CMD(
            msg=msg,
            timeLimit=time_limit,
            gapRel=gap_rel if gap_rel > 0 else None,
        )
    elif name == "GLPK":
        return pulp.GLPK_CMD(msg=msg, timeLimit=time_limit)
    elif name in ("CPLEX", "CPLEX_PY"):
        return pulp.CPLEX_PY(msg=msg, timeLimit=time_limit, epgap=gap_rel)
    elif name == "GUROBI":
        return pulp.GUROBI(msg=msg, timeLimit=time_limit, MIPGap=gap_rel)
    else:
        raise ValueError(
            f"Solver '{name}' no reconocido. "
            "Opciones: CBC, GLPK, CPLEX, GUROBI"
        )
        