"""Problemas con resultados conocidos para cargar y verificar en la interfaz."""

from dataclasses import dataclass

from .model import LPProblem, Point, parse_number


@dataclass(frozen=True)
class Example:
    name: str
    description: str
    problem: LPProblem
    expected_status: str
    expected_point: Point | None
    expected_value: object = None


def make(sense, c, rows):
    return LPProblem.from_strings(sense, c, rows)


EXAMPLES = (
    Example(
        "1 · Maximización con holguras",
        "Max Z = 3x₁ + 2x₂. Solución esperada: (2, 2), Z = 10.",
        make("max", ("3", "2"), (("1", "1", "<=", "4"), ("1", "0", "<=", "2"), ("0", "1", "<=", "3"))),
        "optimal", (parse_number(2), parse_number(2)), parse_number(10),
    ),
    Example(
        "2 · Minimización con artificiales",
        "Min Z = 2x₁ + 3x₂. Solución esperada: (3, 1), Z = 9.",
        make("min", ("2", "3"), (("1", "1", ">=", "4"), ("1", "3", ">=", "6"), ("1", "0", "<=", "5"))),
        "optimal", (parse_number(3), parse_number(1)), parse_number(9),
    ),
    Example(
        "3 · Signos mixtos: =, ≥ y ≤",
        "Max Z = 2x₁ + 3x₂. Solución esperada: (2, 3), Z = 13.",
        make("max", ("2", "3"), (("1", "1", "=", "5"), ("1", "0", ">=", "1"), ("0", "1", "<=", "3"))),
        "optimal", (parse_number(2), parse_number(3)), parse_number(13),
    ),
    Example(
        "4 · Modelo infactible",
        "x₁ + x₂ ≤ 1 y x₁ + x₂ ≥ 3 no pueden cumplirse simultáneamente.",
        make("max", ("1", "1"), (("1", "1", "<=", "1"), ("1", "1", ">=", "3"), ("1", "0", "<=", "4"))),
        "infeasible", None,
    ),
    Example(
        "5 · Objetivo no acotado",
        "La dirección (1, 1) conserva la factibilidad y hace crecer Z = x₁ + x₂.",
        make("max", ("1", "1"), (("1", "-1", ">=", "0"), ("-1", "2", ">=", "0"), ("0", "1", ">=", "1"))),
        "unbounded", None,
    ),
    Example(
        "6 · Múltiples soluciones óptimas",
        "Max Z = x₁ + x₂. Todo el segmento entre (1, 3) y (3, 1) es óptimo: Z = 4.",
        make("max", ("1", "1"), (("1", "1", "<=", "4"), ("1", "0", "<=", "3"), ("0", "1", "<=", "3"))),
        "optimal", None, parse_number(4),
    ),
)
