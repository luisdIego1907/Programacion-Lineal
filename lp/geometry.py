"""Método gráfico independiente del simplex, con geometría racional exacta.

Se enumeran intersecciones de fronteras y direcciones del cono de recesión.
La ventana de la gráfica nunca se usa para decidir si el modelo es acotado.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations

from .model import LPProblem, Point, dot

ZERO = Fraction(0)
ONE = Fraction(1)
AXES = (((ONE, ZERO), ZERO), ((ZERO, ONE), ZERO))


@dataclass(frozen=True)
class Intersection:
    boundaries: tuple[str, str]
    point: Point | None
    feasible: bool


@dataclass(frozen=True)
class GraphicResult:
    status: str
    vertices: tuple[Point, ...]
    vertex_values: tuple[Fraction, ...]
    optimal_vertices: tuple[Point, ...]
    objective_value: Fraction | None
    rays: tuple[Point, ...]
    improving_ray: Point | None
    multiple_optima: bool
    intersections: tuple[Intersection, ...]


def intersect(a: Point, b: Fraction, c: Point, d: Fraction) -> Point | None:
    det = a[0] * c[1] - a[1] * c[0]
    if not det:
        return None
    return ((b * c[1] - a[1] * d) / det, (a[0] * d - b * c[0]) / det)


def recession_rays(problem: LPProblem) -> tuple[Point, ...]:
    candidates = [(ONE, ZERO), (ZERO, ONE)]
    for row in problem.constraints:
        a, b = row.coefficients
        candidates.extend(((b, -a), (-b, a)))
    rays = set()
    for d in candidates:
        if d[0] < 0 or d[1] < 0 or d == (ZERO, ZERO):
            continue
        if all(row.contains(d, homogeneous=True) for row in problem.constraints):
            total = d[0] + d[1]
            rays.add((d[0] / total, d[1] / total))
    return tuple(sorted(rays))


def solve_graphically(problem: LPProblem) -> GraphicResult:
    boundaries = [
        (f"R{i + 1}", row.coefficients, row.rhs)
        for i, row in enumerate(problem.constraints)
    ] + [("x1 = 0", *AXES[0]), ("x2 = 0", *AXES[1])]
    intersections = []
    vertices = set()
    for (name1, a, b), (name2, c, d) in combinations(boundaries, 2):
        point = intersect(a, b, c, d)
        feasible = point is not None and problem.is_feasible(point)
        intersections.append(Intersection((name1, name2), point, feasible))
        if feasible:
            vertices.add(point)
    vertices = tuple(sorted(vertices))
    if not vertices:
        # En el primer cuadrante no hay rectas completas: todo poliedro no
        # vacío contiene al menos un vértice, incluso un segmento o un punto.
        return GraphicResult("infeasible", (), (), (), None, (), None, False, tuple(intersections))

    values = tuple(problem.evaluate(v) for v in vertices)
    rays = recession_rays(problem)
    improving = next((d for d in rays if problem.multiplier * dot(problem.objective, d) > 0), None)
    if improving is not None:
        return GraphicResult(
            "unbounded", vertices, values, (), None, rays, improving, False, tuple(intersections)
        )
    best = max(values) if problem.sense == "max" else min(values)
    optimal = tuple(v for v, value in zip(vertices, values) if value == best)
    multiple = len(optimal) > 1 or any(dot(problem.objective, d) == 0 for d in rays)
    return GraphicResult(
        "optimal", vertices, values, optimal, best, rays, None, multiple, tuple(intersections)
    )


def convex_hull(points: tuple[Point, ...] | list[Point]) -> tuple[Point, ...]:
    points = sorted(set(points))
    if len(points) <= 1:
        return tuple(points)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return tuple(lower[:-1] + upper[:-1])


def visible_region(problem: LPProblem, xmax: Fraction, ymax: Fraction) -> tuple[Point, ...]:
    """Interseca el modelo con la ventana; conserva segmentos y puntos."""
    lines = [(r.coefficients, r.rhs) for r in problem.constraints]
    lines += [*AXES, ((ONE, ZERO), xmax), ((ZERO, ONE), ymax)]
    points = set()
    for (a, b), (c, d) in combinations(lines, 2):
        p = intersect(a, b, c, d)
        if p is not None and 0 <= p[0] <= xmax and 0 <= p[1] <= ymax and problem.is_feasible(p):
            points.add(p)
    return convex_hull(tuple(points))


def clip_line(a: Point, b: Fraction, xmax: Fraction, ymax: Fraction) -> tuple[Point, ...]:
    points = set()
    borders = [*AXES, ((ONE, ZERO), xmax), ((ZERO, ONE), ymax)]
    for c, d in borders:
        p = intersect(a, b, c, d)
        if p is not None and 0 <= p[0] <= xmax and 0 <= p[1] <= ymax:
            points.add(p)
    points = sorted(points)
    return (points[0], points[-1]) if len(points) >= 2 else tuple(points)
