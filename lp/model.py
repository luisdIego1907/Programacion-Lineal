"""Modelo de entrada. Toda la aritmética matemática usa Fraction."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

Point = tuple[Fraction, Fraction]
SIGNS = ("<=", ">=", "=")


def parse_number(value: str | int | float | Fraction) -> Fraction:
    """Acepta enteros, decimales con coma o punto y fracciones p/q."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise ValueError("Ingrese un número, no un valor lógico.")
    text = str(value).strip().replace("−", "-")
    if "," in text and "." in text:
        raise ValueError("Use coma o punto decimal, sin separadores de miles.")
    try:
        return Fraction(text.replace(",", "."))
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"«{value}» no es válido. Ejemplos: 3, -2.5, 1/3.") from exc


def dot(a: Point, b: Point) -> Fraction:
    return a[0] * b[0] + a[1] * b[1]


@dataclass(frozen=True)
class Constraint:
    coefficients: Point
    sign: str
    rhs: Fraction

    def __post_init__(self) -> None:
        if len(self.coefficients) != 2:
            raise ValueError("Cada restricción debe tener dos coeficientes.")
        if self.sign not in SIGNS:
            raise ValueError("Los signos admitidos son <=, >= y =.")
        object.__setattr__(self, "coefficients", tuple(map(parse_number, self.coefficients)))
        object.__setattr__(self, "rhs", parse_number(self.rhs))

    def contains(self, point: Point, homogeneous: bool = False) -> bool:
        activity = dot(self.coefficients, point)
        rhs = Fraction(0) if homogeneous else self.rhs
        if self.sign == "<=":
            return activity <= rhs
        if self.sign == ">=":
            return activity >= rhs
        return activity == rhs


@dataclass(frozen=True)
class LPProblem:
    sense: str
    objective: Point
    constraints: tuple[Constraint, Constraint, Constraint]

    def __post_init__(self) -> None:
        if self.sense not in ("max", "min"):
            raise ValueError("Seleccione maximización o minimización.")
        if len(self.objective) != 2 or len(self.constraints) != 3:
            raise ValueError("El modelo exige dos variables y exactamente tres restricciones.")
        if not all(isinstance(row, Constraint) for row in self.constraints):
            raise ValueError("Las restricciones deben ser objetos Constraint.")
        object.__setattr__(self, "objective", tuple(map(parse_number, self.objective)))
        object.__setattr__(self, "constraints", tuple(self.constraints))

    def is_feasible(self, point: Point) -> bool:
        return all(x >= 0 for x in point) and all(r.contains(point) for r in self.constraints)

    def evaluate(self, point: Point) -> Fraction:
        return dot(self.objective, point)

    @property
    def multiplier(self) -> int:
        """Internamente siempre se maximiza W: W=Z o W=-Z."""
        return 1 if self.sense == "max" else -1

    @classmethod
    def from_strings(
        cls, sense: str, objective: Iterable[str], rows: Iterable[tuple[str, str, str, str]]
    ) -> "LPProblem":
        constraints = tuple(
            Constraint((parse_number(a), parse_number(b)), sign, parse_number(rhs))
            for a, b, sign, rhs in rows
        )
        return cls(sense, tuple(map(parse_number, objective)), constraints)
