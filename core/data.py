"""
data.py — Modelos de dominio para OptiNet (red de transporte MILP).

Jerarquía:
  NetworkData
    ├── List[Plant]          oferta
    ├── List[DistCenter]     CDs opcionales (costo fijo + capacidad)
    ├── List[Client]         demanda + penalización por déficit
    ├── List[Arc]            arcos con costo unitario y capacidad
    └── NetworkConfig        parámetros globales (máx. rutas, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

# ─────────────────────────────────────────────
# Tipos base
# ─────────────────────────────────────────────

NodeType = Literal["plant", "dc", "client"]


@dataclass
class Plant:
    """Nodo de origen (planta productora)."""
    id: str
    name: str
    supply: float                    # unidades disponibles

    def __post_init__(self):
        if self.supply < 0:
            raise ValueError(f"Planta '{self.id}': supply no puede ser negativo.")


@dataclass
class DistCenter:
    """Centro de distribución opcional — decisión binaria de apertura."""
    id: str
    name: str
    fixed_cost: float                # costo de apertura (costo fijo)
    capacity: float                  # capacidad máxima si se abre
    open: bool = False               # estado inicial (para warm-start)

    def __post_init__(self):
        if self.fixed_cost < 0:
            raise ValueError(f"CD '{self.id}': fixed_cost no puede ser negativo.")
        if self.capacity <= 0:
            raise ValueError(f"CD '{self.id}': capacity debe ser > 0.")


@dataclass
class Client:
    """Nodo de destino con demanda y penalización por déficit."""
    id: str
    name: str
    demand: float                    # unidades requeridas
    penalty: float                   # costo por unidad no satisfecha

    def __post_init__(self):
        if self.demand < 0:
            raise ValueError(f"Cliente '{self.id}': demand no puede ser negativo.")
        if self.penalty < 0:
            raise ValueError(f"Cliente '{self.id}': penalty no puede ser negativo.")


@dataclass
class Arc:
    """
    Arco dirigido entre dos nodos cualesquiera.

    origin_type / dest_type permiten distinguir:
      plant  → client    (ruta directa)
      plant  → dc        (tramo de entrada al CD)
      dc     → client    (tramo de salida del CD)
    """
    id: str
    origin_id: str
    origin_type: NodeType
    dest_id: str
    dest_type: NodeType
    unit_cost: float                 # costo por unidad transportada
    capacity: Optional[float] = None # None = sin límite explícito

    def __post_init__(self):
        if self.unit_cost < 0:
            raise ValueError(f"Arco '{self.id}': unit_cost no puede ser negativo.")
        if self.capacity is not None and self.capacity <= 0:
            raise ValueError(f"Arco '{self.id}': capacity debe ser > 0 si se especifica.")


@dataclass
class NetworkConfig:
    """Parámetros globales del modelo."""
    max_active_routes: int = 8       # restricción de conectividad (≤ N rutas activas)
    big_m: float = 1e6               # constante Big-M para restricciones de enlazado
    allow_partial_supply: bool = True  # True → se permiten déficits penalizados

    def __post_init__(self):
        if self.max_active_routes < 1:
            raise ValueError("max_active_routes debe ser al menos 1.")


# ─────────────────────────────────────────────
# Contenedor principal
# ─────────────────────────────────────────────

@dataclass
class NetworkData:
    """
    Grafo completo de la red de transporte.

    Uso típico:
        net = NetworkData(
            plants=[Plant("P1", "Planta 1", 200), ...],
            dist_centers=[DistCenter("CD1", "Centro Norte", 1000, 300), ...],
            clients=[Client("C1", "Cliente A", 150, 25), ...],
            arcs=[Arc("a1", "P1", "plant", "C1", "client", 10), ...],
        )
    """
    plants: list[Plant] = field(default_factory=list)
    dist_centers: list[DistCenter] = field(default_factory=list)
    clients: list[Client] = field(default_factory=list)
    arcs: list[Arc] = field(default_factory=list)
    config: NetworkConfig = field(default_factory=NetworkConfig)

    # ── propiedades de conveniencia ──────────────────────────────────────

    @property
    def total_supply(self) -> float:
        return sum(p.supply for p in self.plants)

    @property
    def total_demand(self) -> float:
        return sum(c.demand for c in self.clients)

    @property
    def supply_gap(self) -> float:
        """Déficit estructural (positivo = demanda insatisfacible en el mejor caso)."""
        return max(0.0, self.total_demand - self.total_supply)

    # ── búsquedas por id ─────────────────────────────────────────────────

    def get_plant(self, pid: str) -> Plant:
        for p in self.plants:
            if p.id == pid:
                return p
        raise KeyError(f"Planta '{pid}' no encontrada.")

    def get_dc(self, did: str) -> DistCenter:
        for d in self.dist_centers:
            if d.id == did:
                return d
        raise KeyError(f"CD '{did}' no encontrado.")

    def get_client(self, cid: str) -> Client:
        for c in self.clients:
            if c.id == cid:
                return c
        raise KeyError(f"Cliente '{cid}' no encontrado.")

    def arcs_from(self, origin_id: str) -> list[Arc]:
        return [a for a in self.arcs if a.origin_id == origin_id]

    def arcs_to(self, dest_id: str) -> list[Arc]:
        return [a for a in self.arcs if a.dest_id == dest_id]

    # ── validación estructural ───────────────────────────────────────────

    def validate(self) -> list[str]:
        """
        Retorna lista de advertencias/errores encontrados.
        No lanza excepción — el solver decide si continuar o no.
        """
        issues: list[str] = []

        ids_plant = {p.id for p in self.plants}
        ids_dc    = {d.id for d in self.dist_centers}
        ids_client = {c.id for c in self.clients}

        # IDs duplicados
        all_ids = list(ids_plant) + list(ids_dc) + list(ids_client)
        seen, dupes = set(), set()
        for nid in all_ids:
            if nid in seen:
                dupes.add(nid)
            seen.add(nid)
        if dupes:
            issues.append(f"IDs duplicados entre nodos: {dupes}")

        # Arcos con nodos inexistentes
        type_map: dict[str, set[str]] = {
            "plant": ids_plant,
            "dc": ids_dc,
            "client": ids_client,
        }
        for arc in self.arcs:
            if arc.origin_id not in type_map.get(arc.origin_type, set()):
                issues.append(
                    f"Arco '{arc.id}': origen '{arc.origin_id}' "
                    f"no existe en nodos de tipo '{arc.origin_type}'."
                )
            if arc.dest_id not in type_map.get(arc.dest_type, set()):
                issues.append(
                    f"Arco '{arc.id}': destino '{arc.dest_id}' "
                    f"no existe en nodos de tipo '{arc.dest_type}'."
                )

        # Déficit estructural
        if self.supply_gap > 0 and not self.config.allow_partial_supply:
            issues.append(
                f"Déficit de {self.supply_gap} unidades y allow_partial_supply=False."
            )

        # Clientes sin arco entrante
        for c in self.clients:
            if not self.arcs_to(c.id):
                issues.append(f"Cliente '{c.id}' no tiene ningún arco entrante.")

        return issues
    