"""
core/ — Motor de optimización de OptiNet.

Exports principales:
    from core import NetworkData, Plant, DistCenter, Client, Arc, NetworkConfig
    from core import build_model, solve, optimize
    from core import SolverResult
"""

from .data import (
    NetworkData,
    NetworkConfig,
    Plant,
    DistCenter,
    Client,
    Arc,
    NodeType,
)
from .model import MILPModel, build_model
from .solver import SolverResult, ArcFlow, DCDecision, ClientResult, solve, optimize

__all__ = [
    # data
    "NetworkData", "NetworkConfig",
    "Plant", "DistCenter", "Client", "Arc", "NodeType",
    # model
    "MILPModel", "build_model",
    # solver
    "SolverResult", "ArcFlow", "DCDecision", "ClientResult",
    "solve", "optimize",
]
