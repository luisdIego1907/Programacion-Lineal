"""Formato de modelos, tablas, operaciones y reporte descargable."""

from fractions import Fraction

from .geometry import GraphicResult
from .model import LPProblem, Point
from .simplex import SimplexResult, StandardForm, Tableau

STATUS_LABELS = {
    "optimal": "Óptimo encontrado",
    "infeasible": "Modelo infactible",
    "unbounded": "Objetivo no acotado",
    "iteration_limit": "Límite de iteraciones",
}
SIGN_TEX = {"<=": r"\le", ">=": r"\ge", "=": "="}
SIGN_TEXT = {"<=": "≤", ">=": "≥", "=": "="}


def fraction_tex(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    return rf"{sign}\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def variable_tex(name: str) -> str:
    return rf"{name[0]}_{{{name[1:]}}}"


def linear_tex(coefficients, names=("x1", "x2")) -> str:
    terms = []
    for coefficient, name in zip(coefficients, names):
        if not coefficient:
            continue
        magnitude = "" if abs(coefficient) == 1 else fraction_tex(abs(coefficient))
        term = magnitude + variable_tex(name)
        if not terms:
            terms.append(("-" if coefficient < 0 else "") + term)
        else:
            terms.append((" - " if coefficient < 0 else " + ") + term)
    return "".join(terms) or "0"


def model_tex(problem: LPProblem) -> str:
    sense = r"\max" if problem.sense == "max" else r"\min"
    rows = [rf"{sense}\quad Z &= {linear_tex(problem.objective)}"]
    rows.extend(
        rf"R_{{{i+1}}}:\quad {linear_tex(row.coefficients)} &{SIGN_TEX[row.sign]} {fraction_tex(row.rhs)}"
        for i, row in enumerate(problem.constraints)
    )
    rows.append(r"x_1, x_2 &\ge 0")
    return r"\begin{aligned}" + r"\\[5pt]".join(rows) + r"\end{aligned}"


def standard_tex(sf: StandardForm) -> str:
    names = [v.name for v in sf.variables]
    rows = [
        rf"{linear_tex(row, names)} &= {fraction_tex(rhs)}"
        for row, rhs in zip(sf.matrix, sf.rhs)
    ]
    rows.append(", ".join(map(variable_tex, names)) + r" &\ge 0")
    return r"\begin{aligned}" + r"\\[5pt]".join(rows) + r"\end{aligned}"


def penalized_objective_tex(sf: StandardForm) -> str:
    expression = linear_tex([c.c for c in sf.costs[:2]])
    artificial = [variable_tex(v.name) for v in sf.variables if v.kind == "artificial"]
    if artificial:
        expression += r" - M\left(" + " + ".join(artificial) + r"\right)"
    return r"\max\quad W = " + expression


def point_tex(point: Point) -> str:
    return rf"\left({fraction_tex(point[0])}, {fraction_tex(point[1])}\right)"


def point_text(point: Point) -> str:
    return f"({point[0]}, {point[1]})"


def tableau_records(tableau: Tableau, sf: StandardForm) -> list[dict]:
    names = [v.name for v in sf.variables]

    def record(label, cb, values, rhs):
        return {"Base": label, "Cᵦ": cb, **dict(zip(names, map(str, values))), "b": str(rhs)}

    records = [record("Cⱼ", "", sf.costs, "")]
    records += [
        record(names[j], str(sf.costs[j]), row[:-1], row[-1])
        for j, row in zip(tableau.basis, tableau.rows)
    ]
    records += [record("Zⱼ", "", tableau.zj, tableau.objective)]
    records += [record("Cⱼ − Zⱼ", "", tableau.reduced_costs, "")]
    return records


def ratio_records(tableau: Tableau, sf: StandardForm, entering: int, ratios) -> list[dict]:
    name = sf.variables[entering].name
    return [
        {
            "Fila": f"F{i+1}", "Básica": sf.variables[j].name,
            "b": str(row[-1]), name: str(row[entering]),
            "Razón b / coeficiente": str(ratio) if ratio is not None else "No aplica (coeficiente ≤ 0)",
        }
        for i, (j, row, ratio) in enumerate(zip(tableau.basis, tableau.rows, ratios))
    ]


def operation_tex(operation) -> str:
    target, pivot = operation.target + 1, operation.pivot_row + 1
    factor = fraction_tex(operation.factor)
    if operation.kind == "divide":
        return rf"F_{{{target}}} \leftarrow F_{{{target}}} \div \left({factor}\right)"
    return rf"F_{{{target}}} \leftarrow F_{{{target}}} - \left({factor}\right) F_{{{pivot}}}"


def balance_records(problem: LPProblem, point: Point) -> list[dict]:
    records = []
    for i, row in enumerate(problem.constraints):
        activity = row.coefficients[0] * point[0] + row.coefficients[1] * point[1]
        if row.sign == "<=":
            name, value = "Holgura", row.rhs - activity
        elif row.sign == ">=":
            name, value = "Superávit", activity - row.rhs
        else:
            name, value = "Igualdad (residuo)", activity - row.rhs
        records.append({
            "Restricción": f"R{i + 1}", "Lado izquierdo": str(activity),
            "Signo": SIGN_TEXT[row.sign], "Lado derecho": str(row.rhs),
            "Medida": name, "Valor": str(value),
            "Activa": "Sí" if activity == row.rhs else "No",
        })
    return records


def methods_agree(problem: LPProblem, simplex: SimplexResult, graphic: GraphicResult) -> bool:
    if simplex.status != graphic.status:
        return False
    if simplex.status == "optimal":
        return (
            simplex.objective_value == graphic.objective_value
            and simplex.point is not None and problem.is_feasible(simplex.point)
        )
    return simplex.status in ("infeasible", "unbounded")


def markdown_table(records: list[dict]) -> str:
    if not records:
        return "Sin filas."
    columns = list(records[0])
    result = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    result += ["| " + " | ".join(str(row[col]).replace("|", r"\|") for col in columns) + " |" for row in records]
    return "\n".join(result)


def build_report(problem: LPProblem, simplex: SimplexResult, graphic: GraphicResult) -> str:
    sf = simplex.standard
    lines = [
        "# Programación lineal · reporte de solución", "", "## Modelo original", "",
        "$$", model_tex(problem), "$$", "", "## Forma estándar y M simbólica", "",
        "Los lados derechos negativos se multiplican por −1, invirtiendo ≤ y ≥.", "",
        "$$", standard_tex(sf), "$$", "", "$$", penalized_objective_tex(sf), "$$", "",
        "W = Z para maximización; W = −Z para minimización, antes de la penalización.", "",
        "M se compara simbólicamente. Se prioriza reducir la suma de artificiales; se usa Bland dentro de cada etapa.", "",
        "Zⱼ = Σ Cᵦᵢ aᵢⱼ; costo reducido = Cⱼ − Zⱼ; W = Σ Cᵦᵢ bᵢ.", "",
        "## Tabla simplex inicial", "", markdown_table(tableau_records(simplex.initial, sf)), "",
    ]
    for step in simplex.steps:
        entering, leaving = sf.variables[step.entering].name, sf.variables[step.leaving].name
        lines += [
            f"## Iteración {step.number}", "",
            f"Entra **{entering}**; sale **{leaving}**; pivote **{step.pivot}** en F{step.pivot_row+1}.", "",
            markdown_table(ratio_records(step.before, sf, step.entering, step.ratios)), "",
            "Operaciones de Gauss–Jordan (en el orden indicado):", "",
        ]
        for operation in step.operations:
            lines += ["$$", operation_tex(operation), "$$", ""]
        lines += ["Se recalculan Zⱼ y Cⱼ − Zⱼ con la nueva base.", "", markdown_table(tableau_records(step.after, sf)), ""]

    lines += ["## Resultado del simplex", "", STATUS_LABELS[simplex.status] + ".", ""]
    if simplex.status == "optimal":
        lines += [
            f"x1 = {simplex.point[0]}, x2 = {simplex.point[1]}, Z = {simplex.objective_value}.", "",
            markdown_table(balance_records(problem, simplex.point)), "",
            "Todas las artificiales valen cero. Los costos reducidos no permiten mejorar W.", "",
        ]
    elif simplex.status == "infeasible":
        lines += [
            f"La suma mínima de artificiales es {simplex.artificial_sum} > 0.", "",
            "Ningún punto satisface simultáneamente las tres restricciones y la no negatividad.", "",
        ]
    elif simplex.status == "unbounded":
        gain = problem.evaluate(simplex.ray)
        lines += [
            "No hay coeficientes positivos en la columna entrante: no existe variable de salida.", "",
            markdown_table(ratio_records(simplex.final, sf, simplex.terminal_entering, simplex.terminal_ratios)), "",
            f"Punto factible: {point_text(simplex.point)}; dirección factible: {point_text(simplex.ray)}.", "",
            f"x(t) = {point_text(simplex.point)} + t {point_text(simplex.ray)}, t ≥ 0; Z(x(t)) = {problem.evaluate(simplex.point)} + t ({gain}).", "",
        ]
    else:
        lines += ["Se alcanzó el límite de pivotes. No se afirma una solución óptima.", ""]

    lines += ["## Método gráfico independiente", "", STATUS_LABELS[graphic.status] + ".", ""]
    vertex_records = [
        {"Vértice": f"V{i+1}", "x1": str(v[0]), "x2": str(v[1]), "Z": str(z), "Óptimo": "Sí" if v in graphic.optimal_vertices else "No"}
        for i, (v, z) in enumerate(zip(graphic.vertices, graphic.vertex_values))
    ]
    lines += [markdown_table(vertex_records), ""]
    if graphic.rays:
        lines += ["La región factible es no acotada. Sus direcciones extremas normalizadas son:", ""]
        lines += [f"- ({d[0]}, {d[1]}), cambio de Z: {problem.evaluate(d)}." for d in graphic.rays]
        lines += [""]
    if graphic.multiple_optima:
        lines += ["Existen múltiples soluciones óptimas: combinaciones convexas de los vértices óptimos y, si corresponde, rayos con cambio de Z igual a cero.", ""]
    lines += [
        "## Comparación", "",
        "Ambos métodos coinciden en el estado y el valor óptimo." if methods_agree(problem, simplex, graphic) else "Los métodos no coinciden o el simplex se interrumpió. Revisar el modelo y la traza.", "",
        "La geometría evalúa vértices y rayos sin utilizar las tablas del simplex. La ventana del dibujo no determina acotación.", "",
    ]
    return "\n".join(lines)
