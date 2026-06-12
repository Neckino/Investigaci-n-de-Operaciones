import copy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core import (
    NetworkData, NetworkConfig,
    Plant, DistCenter, Client, Arc,
    optimize,
)

# ─────────────────────────────────────────────────────────────────
# Red por defecto (escenario "Base")
# Refleja exactamente el problema documentado: oferta=400, demanda=475
# ─────────────────────────────────────────────────────────────────

def _build_default_network() -> NetworkData:
    plants = [
        Plant("P1", "Planta 1", supply=100),   # era 150
        Plant("P2", "Planta 2", supply=140),   # era 120
        Plant("P3", "Planta 3", supply=160),   # era 130
    ]
    dcs = [
        DistCenter("CD1", "Centro Norte", fixed_cost=1000, capacity=180),  # capacidad era 300
        DistCenter("CD2", "Centro Sur",   fixed_cost=900,  capacity=150),  # capacidad era 300
    ]
    clients = [
        Client("C1", "Cliente 1", demand=90,  penalty=20),  # demand era 120, penalty era 25
        Client("C2", "Cliente 2", demand=100, penalty=22),
        Client("C3", "Cliente 3", demand=110, penalty=25),  # penalty era 20
        Client("C4", "Cliente 4", demand=80,  penalty=18),  # demand era 145
        Client("C5", "Cliente 5", demand=95,  penalty=21),  # NUEVO
    ]
    arcs = [
        # ── Planta → Cliente (directas) ──────────────────────────
        Arc("a01", "P1","plant","C1","client", unit_cost=8),
        Arc("a02", "P1","plant","C2","client", unit_cost=11),  # leer de imagen
        Arc("a03", "P1","plant","C3","client", unit_cost=9),
        Arc("a04", "P1","plant","C4","client", unit_cost=10),
        Arc("a05", "P1","plant","C5","client", unit_cost=11),
        Arc("a06", "P2","plant","C1","client", unit_cost=6),
        Arc("a07", "P2","plant","C2","client", unit_cost=8),
        Arc("a08", "P2","plant","C3","client", unit_cost=7),
        Arc("a09", "P2","plant","C4","client", unit_cost=9),
        Arc("a10", "P2","plant","C5","client", unit_cost=8),
        Arc("a11", "P3","plant","C1","client", unit_cost=7),
        Arc("a12", "P3","plant","C2","client", unit_cost=6),
        Arc("a13", "P3","plant","C3","client", unit_cost=5),
        Arc("a14", "P3","plant","C4","client", unit_cost=8),
        Arc("a15", "P3","plant","C5","client", unit_cost=7),
        # ── Planta → CD ──────────────────────────────────────────
        Arc("b01", "P1","plant","CD1","dc", unit_cost=3),
        Arc("b02", "P2","plant","CD1","dc", unit_cost=4),
        Arc("b03", "P1","plant","CD2","dc", unit_cost=3),
        Arc("b04", "P3","plant","CD2","dc", unit_cost=2),
        # ── CD → Cliente ─────────────────────────────────────────
        Arc("c01", "CD1","dc","C1","client", unit_cost=3),
        Arc("c02", "CD1","dc","C2","client", unit_cost=4),
        Arc("c03", "CD1","dc","C4","client", unit_cost=5),
        Arc("c04", "CD1","dc","C5","client", unit_cost=6),
        Arc("c05", "CD2","dc","C3","client", unit_cost=3),  # era 4
        Arc("c06", "CD2","dc","C4","client", unit_cost=4),
        Arc("c07", "CD2","dc","C5","client", unit_cost=5),
    ]
    return NetworkData(
        plants=plants, dist_centers=dcs, clients=clients, arcs=arcs,
        config=NetworkConfig(max_active_routes=8, allow_partial_supply=True),
    )

# ─────────────────────────────────────────────────────────────────
# Estado mutable de la sesión (single-instance, en memoria)
# ─────────────────────────────────────────────────────────────────

_DEFAULT_NET = _build_default_network()
_current_net: NetworkData = copy.deepcopy(_DEFAULT_NET)

# ─────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────

app = FastAPI(title="OptiNet API", version="1.0.0")

STATIC_DIR = Path(__file__).parent / "static"


# ── /api/data ────────────────────────────────────────────────────

@app.get("/api/data")
def get_data() -> dict:
    """
    Devuelve la red en el formato que consume editor.js / dashboard.js:
      plantas, centros, clientes, costos_planta_cliente,
      costos_planta_cd, costos_cd_cliente, max_rutas_activas
    """
    net = _current_net

    plantas  = [{"id": p.id, "nombre": p.name, "oferta": p.supply}     for p in net.plants]
    centros  = [{"id": d.id, "nombre": d.name,
                 "capacidad": d.capacity, "costo_fijo": d.fixed_cost}   for d in net.dist_centers]
    clientes = [{"id": c.id, "nombre": c.name,
                 "demanda": c.demand, "penalizacion": c.penalty}        for c in net.clients]

    costos_pc  = {}   # planta → cliente
    costos_pcd = {}   # planta → CD
    costos_cdc = {}   # CD    → cliente

    for arc in net.arcs:
        key = f"('{arc.origin_id}', '{arc.dest_id}')"
        if arc.origin_type == "plant" and arc.dest_type == "client":
            costos_pc[key] = arc.unit_cost
        elif arc.origin_type == "plant" and arc.dest_type == "dc":
            costos_pcd[key] = arc.unit_cost
        elif arc.origin_type == "dc" and arc.dest_type == "client":
            costos_cdc[key] = arc.unit_cost

    return {
        "plantas":                plantas,
        "centros":                centros,
        "clientes":               clientes,
        "costos_planta_cliente":  costos_pc,
        "costos_planta_cd":       costos_pcd,
        "costos_cd_cliente":      costos_cdc,
        "max_rutas_activas":      net.config.max_active_routes,
    }


# ── /api/solve ───────────────────────────────────────────────────

@app.post("/api/solve")
def solve() -> dict:
    """
    Ejecuta el MILP y devuelve la solución en el formato que consume
    dashboard.js y editor.js (applySolution).
    """
    net = _current_net
    result = optimize(net, msg=False)

    if not result.feasible:
        return {
            "factible": False,
            "estado":   result.status,
            "mensaje":  result.error_message or result.status,
        }

    # ── Flujos por tipo de arco ──────────────────────────────────
    flujo_directo    = {}
    flujo_planta_cd  = {}
    flujo_cd_cliente = {}

    for af in result.arc_flows:
        if not af.active or af.flow == 0:
            continue
        key = f"('{af.origin_id}', '{af.dest_id}')"
        if af.origin_type == "plant" and af.dest_type == "client":
            flujo_directo[key]    = af.flow
        elif af.origin_type == "plant" and af.dest_type == "dc":
            flujo_planta_cd[key]  = af.flow
        elif af.origin_type == "dc" and af.dest_type == "client":
            flujo_cd_cliente[key] = af.flow

    # ── Déficit por cliente ──────────────────────────────────────
    deficit = {
        cr.client_id: cr.deficit
        for cr in result.client_results
        if cr.deficit > 0
    }

    # ── Centros abiertos ────────────────────────────────────────
    centros_abiertos = [
        d.dc_id for d in result.dc_decisions if d.opened
    ]

    # ── Desglose de costos ───────────────────────────────────────
    # El frontend espera: costos_fijos, transporte_directo,
    # transporte_planta_cd, transporte_cd_cliente, penalizaciones
    transp_dir = sum(
        af.total_cost for af in result.arc_flows
        if af.active and af.origin_type == "plant" and af.dest_type == "client"
    )
    transp_pcd = sum(
        af.total_cost for af in result.arc_flows
        if af.active and af.origin_type == "plant" and af.dest_type == "dc"
    )
    transp_cdc = sum(
        af.total_cost for af in result.arc_flows
        if af.active and af.origin_type == "dc" and af.dest_type == "client"
    )

    desglose = {
        "costos_fijos":           result.fixed_cost,
        "transporte_directo":     round(transp_dir, 2),
        "transporte_planta_cd":   round(transp_pcd, 2),
        "transporte_cd_cliente":  round(transp_cdc, 2),
        "penalizaciones":         result.penalty_cost,
    }

    # ── Rutas para KPI ───────────────────────────────────────────
    rutas_directas = [
        {"de": af.origin_id, "a": af.dest_id, "flujo": af.flow}
        for af in result.arc_flows
        if af.active and af.dest_type == "client" and af.origin_type == "plant"
    ]
    rutas_cd = [
        {"de": af.origin_id, "a": af.dest_id, "flujo": af.flow}
        for af in result.arc_flows
        if af.active and (af.origin_type == "dc" or af.dest_type == "dc")
    ]

    return {
        "factible":        True,
        "estado":          result.status,
        "costo_total":     result.total_cost,
        "desglose":        desglose,
        "flujo_directo":   flujo_directo,
        "flujo_planta_cd": flujo_planta_cd,
        "flujo_cd_cliente":flujo_cd_cliente,
        "deficit":         deficit,
        "centros_abiertos":centros_abiertos,
        "rutas_directas":  rutas_directas,
        "rutas_cd":        rutas_cd,
        "tiempo_solver_s": result.solve_time_sec,
        "nivel_servicio":  result.service_level,
    }


# ── /api/nodes ───────────────────────────────────────────────────

class NodeUpdate(BaseModel):
    id: str
    group: str                      # "planta" | "centro" | "cliente"
    changes: dict[str, float]

@app.post("/api/nodes")
def update_node(body: NodeUpdate) -> dict:
    """
    Edita los atributos de un nodo existente en la red en memoria.
    Los cambios persisten hasta el próximo /api/reset.
    """
    global _current_net
    net = _current_net

    if body.group == "planta":
        for p in net.plants:
            if p.id == body.id:
                if "oferta" in body.changes:
                    p.supply = float(body.changes["oferta"])
                return {"ok": True, "id": p.id, "oferta": p.supply}
        raise HTTPException(404, f"Planta '{body.id}' no encontrada")

    if body.group == "centro":
        for d in net.dist_centers:
            if d.id == body.id:
                if "capacidad"  in body.changes: d.capacity   = float(body.changes["capacidad"])
                if "costo_fijo" in body.changes: d.fixed_cost = float(body.changes["costo_fijo"])
                return {"ok": True, "id": d.id, "capacidad": d.capacity, "costo_fijo": d.fixed_cost}
        raise HTTPException(404, f"CD '{body.id}' no encontrado")

    if body.group == "cliente":
        for c in net.clients:
            if c.id == body.id:
                if "demanda"      in body.changes: c.demand  = float(body.changes["demanda"])
                if "penalizacion" in body.changes: c.penalty = float(body.changes["penalizacion"])
                return {"ok": True, "id": c.id, "demanda": c.demand, "penalizacion": c.penalty}
        raise HTTPException(404, f"Cliente '{body.id}' no encontrado")

    raise HTTPException(400, f"Grupo '{body.group}' inválido")


# ── /api/params ──────────────────────────────────────────────────

class ParamsUpdate(BaseModel):
    max_rutas_activas: int = Field(8, ge=1, le=100)

@app.post("/api/params")
def update_params(body: ParamsUpdate) -> dict:
    """Actualiza parámetros del solver (max_rutas_activas)."""
    _current_net.config.max_active_routes = body.max_rutas_activas
    return {"ok": True, "max_rutas_activas": body.max_rutas_activas}


# ── /api/reset ───────────────────────────────────────────────────

@app.post("/api/reset")
def reset() -> dict:
    """Reinicia la red en memoria a los valores del escenario Base."""
    global _current_net
    _current_net = copy.deepcopy(_DEFAULT_NET)
    return {"ok": True, "mensaje": "Red reiniciada al escenario Base"}


# ── Static files + SPA fallback ──────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_spa() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


# ─────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    