from dataclasses import dataclass, field
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

# costo_planta_centro[planta_id][centro_id]
# Nota: la imagen no muestra costos P→CD explícitos; se usa costo directo
# planta→cliente cuando no hay CD intermedio requerido por el modelo.
# El modelo es de dos escalones: Planta → CD → Cliente.
# Los costos planta→cliente de la imagen son los costos del primer tramo
# interpretados como planta→CD (proxy), y los costos CD→cliente son el segundo.

# Costos planta → cliente (tabla imagen, usados como costo planta→CD aproximado
# cuando el flujo pasa por un CD; aquí se modelan como costo directo P→CD
# asumiendo distribución uniforme hacia cada CD según la tabla disponible).
# Para este modelo de 2 escalones exactos, necesitamos P→CD y CD→C por separado.
# La imagen provee: tabla "Costos planta→cliente" (usada como costo etapa 1)
# y tabla "Costos CD→cliente" (etapa 2). Interpretamos P→CD como el promedio
# de la fila de la planta en la tabla P→C (costo de primer tramo genérico),
# y CD→C directamente de la tabla.

# Costos planta → centro de distribución
# (extraídos de la tabla "Costos planta → cliente" de la imagen,
#  columnas C1..C5 como referencia de costo de primer tramo;
#  se asigna costo_planta_cd como mínimo de la fila para reflejar
#  el costo de enviar desde la planta hacia el hub más económico)
# Valores directos de la imagen por fila de planta (se usan las columnas
# de la tabla como costo de envío planta→CD; CD1 corresponde a columnas
# de menor índice, CD2 a las de mayor, siguiendo la convención del ejercicio)

#         CD1   CD2
COSTO_PLANTA_CD: Dict[Tuple[str, str], float] = {
    ("P1", "CD1"): 8,
    ("P1", "CD2"): 11,
    ("P2", "CD1"): 6,
    ("P2", "CD2"): 8,
    ("P3", "CD1"): 7,
    ("P3", "CD2"): 7,
}

# Costos CD → cliente (tabla imagen "Costos CD → cliente")
#         C1  C2  C3  C4  C5
COSTO_CD_CLIENTE: Dict[Tuple[str, str], float] = {
    ("CD1", "C1"): 3, ("CD1", "C2"): 4, ("CD1", "C3"): 5, ("CD1", "C4"): 6, ("CD1", "C5"): 6,
    ("CD2", "C1"): 5, ("CD2", "C2"): 3, ("CD2", "C3"): 4, ("CD2", "C4"): 4, ("CD2", "C5"): 5,
}

MAX_RUTAS_ACTIVAS = 8
