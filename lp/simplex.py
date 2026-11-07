"""Simplex primal implementado explícitamente, con M simbólica y regla de Bland.

No se llama a ningún optimizador externo. Los coeficientes de las restricciones
son racionales; los costos son pares (coeficiente de M, término independiente).
"""

from dataclasses import dataclass
from fractions import Fraction

from .model import LPProblem, Point

ZERO = Fraction(0)
ONE = Fraction(1)


@dataclass(frozen=True)
class BigM:
    """Expresión m*M + c. M es mayor que cualquier constante finita."""
    m: Fraction = ZERO
    c: Fraction = ZERO

    def __add__(self, other: "BigM") -> "BigM":
        return BigM(self.m + other.m, self.c + other.c)

    def __sub__(self, other: "BigM") -> "BigM":
        return BigM(self.m - other.m, self.c - other.c)

    def __mul__(self, scalar: Fraction) -> "BigM":
        return BigM(self.m * scalar, self.c * scalar)

    def is_positive(self) -> bool:
        return (self.m, self.c) > (ZERO, ZERO)

    def __str__(self) -> str:
        if not self.m:
            return str(self.c)
        if self.m == 1:
            text = "M"
        elif self.m == -1:
            text = "-M"
        else:
            text = f"{self.m} M"
        if self.c:
            text += f" {'+' if self.c > 0 else '-'} {abs(self.c)}"
        return text


@dataclass(frozen=True)
class Variable:
    name: str
    kind: str  # decision, slack, surplus, artificial
    constraint: int | None = None


@dataclass(frozen=True)
class StandardForm:
    variables: tuple[Variable, ...]
    matrix: tuple[tuple[Fraction, ...], ...]
    rhs: tuple[Fraction, ...]
    basis: tuple[int, ...]
    costs: tuple[BigM, ...]
    flipped: tuple[bool, ...]
    normalized_signs: tuple[str, ...]
    multiplier: int


@dataclass(frozen=True)
class Tableau:
    rows: tuple[tuple[Fraction, ...], ...]  # última columna = b
    basis: tuple[int, ...]
    zj: tuple[BigM, ...]
    reduced_costs: tuple[BigM, ...]
    objective: BigM


@dataclass(frozen=True)
class RowOperation:
    target: int
    pivot_row: int
    factor: Fraction
    kind: str  # divide, subtract


@dataclass(frozen=True)
class PivotStep:
    number: int
    entering: int
    leaving: int
    pivot_row: int
    pivot: Fraction
    ratios: tuple[Fraction | None, ...]
    operations: tuple[RowOperation, ...]
    before: Tableau
    after: Tableau


@dataclass(frozen=True)
class SimplexResult:
    status: str  # optimal, infeasible, unbounded, iteration_limit
    standard: StandardForm
    initial: Tableau
    steps: tuple[PivotStep, ...]
    final: Tableau
    values: tuple[Fraction, ...]
    point: Point | None
    objective_value: Fraction | None
    artificial_sum: Fraction
    ray: Point | None = None
    terminal_entering: int | None = None
    terminal_ratios: tuple[Fraction | None, ...] = ()


def standardize(problem: LPProblem) -> StandardForm:
    """Normaliza b>=0, agrega h, e y a; construye una base identidad."""
    variables = [Variable("x1", "decision"), Variable("x2", "decision")]
    matrix = [list(r.coefficients) for r in problem.constraints]
    rhs = []
    signs = []
    flipped = []
    for i, row in enumerate(problem.constraints):
        flip = row.rhs < 0
        flipped.append(flip)
        rhs.append(-row.rhs if flip else row.rhs)
        sign = row.sign
        if flip:
            matrix[i] = [-x for x in matrix[i]]
            sign = {"<=": ">=", ">=": "<=", "=": "="}[sign]
        signs.append(sign)

    costs = [BigM(c=problem.multiplier * c) for c in problem.objective]
    basis = []

    def add_column(name: str, kind: str, row: int, coefficient: int) -> int:
        col = len(variables)
        variables.append(Variable(name, kind, row))
        for i in range(3):
            matrix[i].append(Fraction(coefficient if i == row else 0))
        costs.append(BigM(m=-ONE) if kind == "artificial" else BigM())
        return col

    for i, sign in enumerate(signs):
        if sign == "<=":
            basis.append(add_column(f"h{i + 1}", "slack", i, 1))
        else:
            if sign == ">=":
                add_column(f"e{i + 1}", "surplus", i, -1)
            basis.append(add_column(f"a{i + 1}", "artificial", i, 1))

    return StandardForm(
        tuple(variables), tuple(tuple(row) for row in matrix), tuple(rhs),
        tuple(basis), tuple(costs), tuple(flipped), tuple(signs), problem.multiplier,
    )


def make_tableau(rows, basis, costs) -> Tableau:
    rows = tuple(tuple(row) for row in rows)
    basis = tuple(basis)
    n = len(costs)
    zj = tuple(
        sum((costs[basis[i]] * row[j] for i, row in enumerate(rows)), BigM())
        for j in range(n)
    )
    objective = sum(
        (costs[basis[i]] * row[-1] for i, row in enumerate(rows)), BigM()
    )
    return Tableau(rows, basis, zj, tuple(costs[j] - zj[j] for j in range(n)), objective)


def basic_values(tableau: Tableau, n: int) -> tuple[Fraction, ...]:
    values = [ZERO] * n
    for i, j in enumerate(tableau.basis):
        values[j] = tableau.rows[i][-1]
    return tuple(values)


def solve_simplex(problem: LPProblem, max_iterations: int = 1000) -> SimplexResult:
    """Resuelve con Gauss–Jordan y devuelve toda la traza matemática.

    Se atienden primero los costos reducidos con componente M positiva.
    Dentro de esa etapa y luego con los costos finitos se usa Bland: menor
    índice de columna; empates de razón se rompen por índice de variable básica.
    Así no se confunde una dirección de mejora del objetivo con factibilidad.
    """
    if max_iterations < 0:
        raise ValueError("El máximo de iteraciones debe ser no negativo.")
    sf = standardize(problem)
    n = len(sf.variables)
    rows = [list(row) + [b] for row, b in zip(sf.matrix, sf.rhs)]
    tableau = make_tableau(rows, sf.basis, sf.costs)
    initial = tableau
    steps = []

    def finish(status, entering=None, ratios=(), ray=None):
        values = basic_values(tableau, n)
        art = sum((v for v, var in zip(values, sf.variables) if var.kind == "artificial"), ZERO)
        feasible = status in ("optimal", "unbounded")
        point = (values[0], values[1]) if feasible else None
        return SimplexResult(
            status, sf, initial, tuple(steps), tableau, values, point,
            problem.evaluate(point) if status == "optimal" else None,
            art, ray, entering, tuple(ratios),
        )

    while True:
        values = basic_values(tableau, n)
        artificial_sum = sum(
            (v for v, var in zip(values, sf.variables) if var.kind == "artificial"), ZERO
        )
        nonbasic = [j for j in range(n) if j not in tableau.basis]
        penalty_candidates = [j for j in nonbasic if tableau.reduced_costs[j].m > 0]

        if penalty_candidates:
            entering = min(penalty_candidates)
        elif artificial_sum > 0:
            # -sum(a) ya está maximizado; una mejora finita no corrige esto.
            return finish("infeasible")
        else:
            candidates = [j for j in nonbasic if tableau.reduced_costs[j].is_positive()]
            if not candidates:
                return finish("optimal")
            entering = min(candidates)

        ratios = tuple(
            row[-1] / row[entering] if row[entering] > 0 else None
            for row in tableau.rows
        )
        eligible_rows = [i for i, ratio in enumerate(ratios) if ratio is not None]
        if not eligible_rows:
            direction = [ZERO] * n
            direction[entering] = ONE
            for i, j in enumerate(tableau.basis):
                direction[j] = -tableau.rows[i][entering]
            return finish("unbounded", entering, ratios, (direction[0], direction[1]))

        if len(steps) >= max_iterations:
            return finish("iteration_limit", entering, ratios)

        pivot_row = min(eligible_rows, key=lambda i: (ratios[i], tableau.basis[i]))
        pivot = tableau.rows[pivot_row][entering]
        leaving = tableau.basis[pivot_row]
        rows = [list(row) for row in tableau.rows]
        operations = [RowOperation(pivot_row, pivot_row, pivot, "divide")]
        rows[pivot_row] = [x / pivot for x in rows[pivot_row]]
        for i in range(len(rows)):
            if i == pivot_row:
                continue
            factor = rows[i][entering]
            if factor:
                rows[i] = [x - factor * y for x, y in zip(rows[i], rows[pivot_row])]
                operations.append(RowOperation(i, pivot_row, factor, "subtract"))
        basis = list(tableau.basis)
        basis[pivot_row] = entering
        after = make_tableau(rows, basis, sf.costs)
        steps.append(PivotStep(
            len(steps) + 1, entering, leaving, pivot_row, pivot, ratios,
            tuple(operations), tableau, after,
        ))
        tableau = after
