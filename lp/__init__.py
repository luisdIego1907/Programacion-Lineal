"""Programación lineal exacta con dos variables y tres restricciones."""

from .model import Constraint, LPProblem, parse_number
from .simplex import solve_simplex
from .geometry import solve_graphically

__all__ = ["Constraint", "LPProblem", "parse_number", "solve_simplex", "solve_graphically"]
