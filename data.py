from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class Planta:
    id: str
    oferta: float


@dataclass
class Cliente:
    id: str
    demanda: float
    penalizacion: float


@dataclass
class Centro:
    id: str
    capacidad: float
    costo_fijo: float


# ── Nodos ─────────────────────────────────────────────────────────────────────

PLANTAS = [
    Planta("P1", oferta=100),
    Planta("P2", oferta=140),
    Planta("P3", oferta=160),
]

CLIENTES = [
    Cliente("C1", demanda=90,  penalizacion=20),
    Cliente("C2", demanda=100, penalizacion=22),
    Cliente("C3", demanda=110, penalizacion=25),
    Cliente("C4", demanda=80,  penalizacion=18),
    Cliente("C5", demanda=95,  penalizacion=21),
]

CENTROS = [
    Centro("CD1", capacidad=180, costo_fijo=1000),
    Centro("CD2", capacidad=150, costo_fijo=900),
]

# ── Costos de transporte ───────────────────────────────────────────────────────

# Tabla "Costos planta → cliente" de la imagen (ruta directa)
#           C1   C2   C3   C4   C5
COSTO_PLANTA_CLIENTE: Dict[Tuple[str, str], float] = {
    ("P1", "C1"): 8,  ("P1", "C2"): 7,  ("P1", "C3"): 9,  ("P1", "C4"): 10, ("P1", "C5"): 11,
    ("P2", "C1"): 6,  ("P2", "C2"): 8,  ("P2", "C3"): 7,  ("P2", "C4"): 9,  ("P2", "C5"): 8,
    ("P3", "C1"): 7,  ("P3", "C2"): 6,  ("P3", "C3"): 5,  ("P3", "C4"): 8,  ("P3", "C5"): 7,
}

# Tabla "Costos planta → CD" (primer tramo vía CD)
# Interpretados de la imagen: columnas de menor índice → CD1, mayores → CD2
#           CD1  CD2
COSTO_PLANTA_CD: Dict[Tuple[str, str], float] = {
    ("P1", "CD1"): 8,  ("P1", "CD2"): 11,
    ("P2", "CD1"): 6,  ("P2", "CD2"): 8,
    ("P3", "CD1"): 7,  ("P3", "CD2"): 7,
}

# Tabla "Costos CD → cliente" de la imagen (segundo tramo vía CD)
#            C1  C2  C3  C4  C5
COSTO_CD_CLIENTE: Dict[Tuple[str, str], float] = {
    ("CD1", "C1"): 3, ("CD1", "C2"): 4, ("CD1", "C3"): 5, ("CD1", "C4"): 6, ("CD1", "C5"): 6,
    ("CD2", "C1"): 5, ("CD2", "C2"): 3, ("CD2", "C3"): 4, ("CD2", "C4"): 4, ("CD2", "C5"): 5,
}

MAX_RUTAS_ACTIVAS = 8
