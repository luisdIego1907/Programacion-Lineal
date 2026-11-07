"""Interfaz educativa en Streamlit. Ejecutar: python -m streamlit run app.py."""

import json
from fractions import Fraction
from math import isfinite

import streamlit as st

from lp.examples import EXAMPLES
from lp.geometry import solve_graphically
from lp.model import Constraint, LPProblem, parse_number
from lp.plotting import build_figure, default_limits
from lp.presentation import (
    STATUS_LABELS, balance_records, build_report, fraction_tex, methods_agree,
    model_tex, operation_tex, penalized_objective_tex, point_tex,
    ratio_records, standard_tex, tableau_records, variable_tex,
)
from lp.simplex import solve_simplex


st.set_page_config(page_title="Programación lineal · Simplex y gráfico", page_icon="📐", layout="wide")
st.markdown("""
<style>
    .block-container { max-width: 1440px; padding-top: 4.5rem; }
    h1 { letter-spacing: -0.04em; }
    h2, h3 { letter-spacing: -0.025em; }
    [data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; }
    [data-testid="stForm"] { background: #ffffff; }
    .eyebrow { color: #166b57; font-size: .75rem; font-weight: 700;
               letter-spacing: .15em; margin-bottom: .35rem; }
</style>
""", unsafe_allow_html=True)


def load_example(index: int) -> None:
    problem = EXAMPLES[index].problem
    st.session_state["sense"] = "Maximizar" if problem.sense == "max" else "Minimizar"
    for j, c in enumerate(problem.objective):
        st.session_state[f"c{j+1}"] = str(c)
    for i, row in enumerate(problem.constraints):
        st.session_state[f"r{i}_a"] = str(row.coefficients[0])
        st.session_state[f"r{i}_b"] = str(row.coefficients[1])
        st.session_state[f"r{i}_sign"] = {"<=": "≤", ">=": "≥", "=": "="}[row.sign]
        st.session_state[f"r{i}_rhs"] = str(row.rhs)
    st.session_state["pending_example"] = True


def field_number(key: str, label: str) -> Fraction:
    try:
        return parse_number(st.session_state[key])
    except ValueError as exc:
        raise ValueError(f"{label}: {exc}") from exc


def read_problem() -> LPProblem:
    objective = tuple(field_number(f"c{j+1}", f"Objetivo, coeficiente de x{j+1}") for j in range(2))
    constraints = []
    for i in range(3):
        constraints.append(Constraint(
            (field_number(f"r{i}_a", f"R{i+1}, coeficiente de x1"), field_number(f"r{i}_b", f"R{i+1}, coeficiente de x2")),
            {"≤": "<=", "≥": ">=", "=": "="}[st.session_state[f"r{i}_sign"]],
            field_number(f"r{i}_rhs", f"R{i+1}, lado derecho"),
        ))
    return LPProblem("max" if st.session_state["sense"] == "Maximizar" else "min", objective, tuple(constraints))


def show_tableau(tableau, standard) -> None:
    st.dataframe(tableau_records(tableau, standard), hide_index=True, width="stretch")


def show_terminal(problem, simplex) -> None:
    sf = simplex.standard
    if simplex.status == "optimal":
        st.success("No hay costos reducidos positivos. Todas las artificiales valen cero: la solución es factible y óptima.")
        zero_art = [sf.variables[j].name for j in simplex.final.basis if sf.variables[j].kind == "artificial"]
        if zero_art:
            st.info("Artificiales básicas con valor cero: " + ", ".join(zero_art) + ". Esto es degeneración y no implica infactibilidad.")
    elif simplex.status == "infeasible":
        st.error(f"La suma mínima de artificiales es {simplex.artificial_sum} > 0. El modelo original es infactible.")
        st.caption("Ya no hay costos reducidos con componente M positiva. Mejorar la parte finita del objetivo no elimina esta incompatibilidad.")
    elif simplex.status == "unbounded":
        name = sf.variables[simplex.terminal_entering].name
        st.warning(f"La variable {name} puede entrar, pero su columna no tiene coeficientes positivos. No existe variable de salida.")
        st.dataframe(ratio_records(simplex.final, sf, simplex.terminal_entering, simplex.terminal_ratios), hide_index=True, width="stretch")
        show_ray(problem, simplex.point, simplex.ray)
    else:
        st.warning("Se alcanzó el límite de iteraciones. No se afirma que el último punto sea óptimo.")


def show_ray(problem, anchor, ray) -> None:
    st.latex(rf"x(t) = {point_tex(anchor)} + t\,{point_tex(ray)},\qquad t\ge 0")
    gain = problem.evaluate(ray)
    base = problem.evaluate(anchor)
    infinity = r"+\infty" if problem.sense == "max" else r"-\infty"
    st.latex(rf"Z(x(t)) = {fraction_tex(base)} + t\left({fraction_tex(gain)}\right)\longrightarrow {infinity}")
    st.caption("El punto inicial y toda esta semirrecta cumplen las restricciones originales y la no negatividad.")


@st.cache_data
def verify_examples() -> list[dict]:
    rows = []
    for example in EXAMPLES:
        sx, gr = solve_simplex(example.problem), solve_graphically(example.problem)
        ok = sx.status == example.expected_status and methods_agree(example.problem, sx, gr)
        if example.expected_value is not None:
            ok = ok and sx.objective_value == example.expected_value
        if example.expected_point is not None:
            ok = ok and sx.point == example.expected_point
        rows.append({
            "Ejemplo": example.name, "Esperado": STATUS_LABELS[example.expected_status],
            "Simplex": STATUS_LABELS[sx.status], "Gráfico": STATUS_LABELS[gr.status],
            "Z esperado": str(example.expected_value) if example.expected_value is not None else "—",
            "Z calculado": str(sx.objective_value) if sx.objective_value is not None else "—",
            "Verificación": "Correcto" if ok else "Revisar",
        })
    return rows


if "sense" not in st.session_state:
    load_example(0)

with st.sidebar:
    st.markdown('<div class="eyebrow">LABORATORIO DE OPTIMIZACIÓN</div>', unsafe_allow_html=True)
    st.title("Explorar un modelo")
    st.caption("Dos variables de decisión y tres restricciones, con x₁, x₂ ≥ 0.")
    choice = st.selectbox("Problemas de prueba", range(len(EXAMPLES)), format_func=lambda i: EXAMPLES[i].name, key="example_choice")
    st.caption(EXAMPLES[choice].description)
    st.button("Cargar ejemplo", on_click=load_example, args=(choice,), width="stretch")
    st.divider()
    st.markdown("**Cómo usar la herramienta**")
    st.markdown("1. Ingrese el objetivo y las tres restricciones.\n2. Pulse **Resolver modelo**.\n3. Explore las tablas y la gráfica.\n4. Descargue el procedimiento.")
    st.divider()
    st.caption("Aritmética racional exacta · M simbólica · Simplex implementado en Python")

st.markdown('<div class="eyebrow">SIMPLEX + MÉTODO GRÁFICO</div>', unsafe_allow_html=True)
st.title("Programación lineal")
st.write("Formule el problema, siga cada pivote y compruebe el resultado en el plano.")

input_col, model_col = st.columns([1.15, 1], gap="large")
with input_col:
    with st.form("model_form"):
        st.subheader("1. Ingresar los datos")
        st.radio("Sentido de la optimización", ("Maximizar", "Minimizar"), key="sense", horizontal=True)
        c1, c2 = st.columns(2)
        c1.text_input("Objetivo · coeficiente de x₁", key="c1", max_chars=40)
        c2.text_input("Objetivo · coeficiente de x₂", key="c2", max_chars=40)
        st.markdown("**Restricciones**")
        for i in range(3):
            cols = st.columns([1, 1, .8, 1])
            cols[0].text_input(f"R{i+1} · x₁", key=f"r{i}_a", max_chars=40)
            cols[1].text_input(f"R{i+1} · x₂", key=f"r{i}_b", max_chars=40)
            cols[2].selectbox(f"R{i+1} · signo", ("≤", "≥", "="), key=f"r{i}_sign")
            cols[3].text_input(f"R{i+1} · b", key=f"r{i}_rhs", max_chars=40, help="Lado derecho de la restricción.")
        st.caption("Ejemplos de entrada: 3, −2.5, 0,25 o 1/3. Use coeficiente 0 cuando una variable no aparezca.")
        submitted = st.form_submit_button("Resolver modelo", type="primary", width="stretch")

if submitted or st.session_state.pop("pending_example", False) or "solution" not in st.session_state:
    # El indicador se limpia también si hubo envío del formulario (cortocircuito).
    st.session_state["pending_example"] = False
    try:
        problem = read_problem()
        sx, gr = solve_simplex(problem), solve_graphically(problem)
        st.session_state["solution"] = (problem, sx, gr)
        limit_x, limit_y = default_limits(gr)
        st.session_state["graph_xmax"] = limit_x
        st.session_state["graph_ymax"] = limit_y
    except (ValueError, OverflowError) as exc:
        st.error(str(exc))
        st.stop()

problem, simplex, graphic = st.session_state["solution"]

with model_col:
    with st.container(border=True):
        st.subheader("2. Modelo resuelto")
        st.latex(model_tex(problem))
        st.caption("El resultado corresponde a este modelo. Después de editar los campos, pulse Resolver modelo para actualizarlo.")
    if simplex.status == "optimal":
        st.success("Óptimo encontrado")
        metrics = st.columns(3)
        metrics[0].metric("x₁", str(simplex.point[0]))
        metrics[1].metric("x₂", str(simplex.point[1]))
        metrics[2].metric("Z óptimo", str(simplex.objective_value))
        st.caption(f"{len(simplex.steps)} pivotes · " + ("Existen múltiples soluciones óptimas." if graphic.multiple_optima else "Solución óptima única."))
    elif simplex.status == "infeasible":
        st.error("Modelo infactible")
        st.write("No existe un punto que cumpla todas las restricciones.")
    elif simplex.status == "unbounded":
        st.warning("Objetivo no acotado")
        st.write("Hay puntos factibles y una dirección que mejora el objetivo sin límite.")
    else:
        st.warning(STATUS_LABELS[simplex.status])

st.divider()
summary_tab, simplex_tab, graph_tab, check_tab = st.tabs([
    "Resultado e interpretación", "Simplex paso a paso", "Método gráfico", "Verificación y descarga",
])

with summary_tab:
    st.subheader("3. Interpretar el resultado")
    if simplex.status == "optimal":
        st.latex(rf"(x_1^*,x_2^*) = {point_tex(simplex.point)},\qquad Z^* = {fraction_tex(simplex.objective_value)}")
        sense_word = "mayor" if problem.sense == "max" else "menor"
        st.write(f"El {sense_word} valor posible de la función objetivo es {simplex.objective_value}. Las tres restricciones y las condiciones de no negatividad se cumplen en el punto mostrado.")
        st.dataframe(balance_records(problem, simplex.point), hide_index=True, width="stretch")
        st.caption("Holgura = b − lado izquierdo para ≤. Superávit = lado izquierdo − b para ≥. En una igualdad el residuo debe ser cero. Una restricción está activa cuando se cumple con igualdad.")
        extra = [{"Variable": v.name, "Tipo": {"slack": "Holgura", "surplus": "Superávit", "artificial": "Artificial"}[v.kind], "Valor": str(value)} for v, value in zip(simplex.standard.variables, simplex.values) if v.kind != "decision"]
        with st.expander("Valores de las variables de la forma estándar"):
            st.dataframe(extra, hide_index=True, width="stretch")
            st.caption("Estos nombres corresponden a las restricciones normalizadas. Si se multiplicó una fila por −1, se invirtió su signo antes de agregar variables.")
        if graphic.multiple_optima:
            st.info("Hay múltiples soluciones óptimas. Cualquier combinación convexa de los vértices óptimos también es óptima; se pueden sumar direcciones factibles cuyo cambio de Z sea cero.")
            st.latex(r"\text{Vértices óptimos: } " + r",\quad ".join(point_tex(v) for v in graphic.optimal_vertices))
        if graphic.rays:
            st.info("La región factible es no acotada, pero el valor óptimo de este objetivo es finito. La acotación de la región y la del objetivo se analizan por separado.")
    elif simplex.status == "infeasible":
        st.write("Las restricciones son incompatibles: la región factible está vacía y no existen valores óptimos de x₁, x₂ ni Z.")
        st.latex(rf"\min\sum_i a_i = {fraction_tex(simplex.artificial_sum)} > 0")
        st.write("Las artificiales permiten construir la base inicial. Como no es posible hacerlas todas cero, no se logra satisfacer el sistema original.")
    elif simplex.status == "unbounded":
        st.write("El modelo es factible. La siguiente semirrecta permanece dentro de la región factible y mejora el objetivo indefinidamente, por lo que no hay óptimo finito.")
        show_ray(problem, simplex.point, simplex.ray)
    else:
        st.write("El algoritmo se detuvo por el límite de iteraciones. La última tabla se conserva para examinarla.")

with simplex_tab:
    st.subheader("Transformar a ecuaciones")
    sf = simplex.standard
    for i, flipped in enumerate(sf.flipped):
        if flipped:
            st.info(f"R{i+1}: lado derecho negativo. Se multiplicó toda la restricción por −1 y se invirtió ≤ ↔ ≥; la igualdad conserva su signo.")
    st.latex(standard_tex(sf))
    st.caption("hᵢ: holgura, con coeficiente +1 en ≤. eᵢ: superávit, con coeficiente −1 en ≥. aᵢ: artificial, con coeficiente +1 en ≥ o =. Todas son no negativas.")
    st.latex(penalized_objective_tex(sf))
    st.caption("Para minimizar se maximiza −Z. M es simbólica y positiva: tiene prioridad sobre cualquier coeficiente finito; no se reemplaza por un número grande.")
    st.markdown("**Convención de la tabla**")
    st.latex(r"Z_j = \sum_i C_{B_i}\,a_{ij},\qquad r_j = C_j-Z_j,\qquad W = \sum_i C_{B_i}\,b_i")
    st.write("Se priorizan columnas con componente M positiva en rⱼ. Dentro de esa etapa, y luego entre costos finitos positivos, entra la variable de menor índice (regla de Bland). Sale la de menor razón bᵢ/aᵢⱼ, usando solo aᵢⱼ > 0. Si hay empate, sale la variable básica de menor índice.")
    st.caption("El orden de índices es el orden de las columnas de la tabla. Una razón cero sí participa. En la fila Zⱼ, la columna b muestra el valor penalizado de W.")
    st.markdown("**Tabla inicial**")
    show_tableau(simplex.initial, sf)
    expand_all = st.toggle("Expandir todas las iteraciones", value=False)
    for step in simplex.steps:
        entering, leaving = sf.variables[step.entering].name, sf.variables[step.leaving].name
        with st.expander(f"Iteración {step.number} · entra {entering} · sale {leaving}", expanded=expand_all or step.number == 1):
            cols = st.columns(4)
            cols[0].metric("Entrada", entering)
            cols[1].metric("Salida", leaving)
            cols[2].metric("Pivote", str(step.pivot))
            cols[3].metric("Razón mínima", str(step.ratios[step.pivot_row]))
            st.caption(f"Costo reducido de {entering}: {step.before.reduced_costs[step.entering]}. Pivote en F{step.pivot_row+1}, columna {entering}.")
            st.dataframe(ratio_records(step.before, sf, step.entering, step.ratios), hide_index=True, width="stretch")
            st.markdown("**Operaciones de Gauss–Jordan**")
            st.latex(r"\begin{aligned}" + r"\\[4pt]".join(operation_tex(op) for op in step.operations) + r"\end{aligned}")
            st.caption("Se normaliza primero la fila pivote; luego se usan sus valores actualizados para anular las demás entradas de la columna. Zⱼ y Cⱼ − Zⱼ se recalculan con la nueva base.")
            show_tableau(step.after, sf)
    st.markdown("**Criterio de terminación**")
    show_terminal(problem, simplex)

with graph_tab:
    st.subheader("Rectas, región factible y vértices")
    st.caption("Arrastre para desplazar, acerque con el zoom y pase el cursor sobre los puntos. La cámara permite guardar la gráfica como SVG.")
    for i, row in enumerate(problem.constraints):
        if not any(row.coefficients):
            st.caption(f"R{i+1} tiene coeficientes cero: es una condición constante y no define una recta.")
    control_x, control_y, _ = st.columns([1, 1, 2])
    xmax = control_x.number_input("Límite de x₁", min_value=1e-9, key="graph_xmax", format="%g")
    ymax = control_y.number_input("Límite de x₂", min_value=1e-9, key="graph_ymax", format="%g")
    if isfinite(xmax) and isfinite(ymax):
        figure = build_figure(problem, graphic, xmax, ymax)
        st.plotly_chart(figure, width="stretch", config={"displaylogo": False, "toImageButtonOptions": {"format": "svg", "filename": "region_factible"}})
    else:
        st.error("Los límites de la gráfica deben ser finitos.")
    if graphic.status == "infeasible":
        st.error("No hay región factible ni vértices factibles.")
    else:
        if graphic.rays:
            st.info("La región factible se extiende fuera de la ventana. Los bordes del dibujo son un recorte y no son restricciones adicionales.")
        if not any(problem.objective):
            st.info("El objetivo es constante: Z = 0. Todo punto factible es óptimo.")
        st.markdown("**Evaluación de la función objetivo en los vértices factibles**")
        st.dataframe([
            {"Vértice": f"V{i+1}", "x₁": str(v[0]), "x₂": str(v[1]), "Z": str(z), "Óptimo": "Sí" if v in graphic.optimal_vertices else "No"}
            for i, (v, z) in enumerate(zip(graphic.vertices, graphic.vertex_values))
        ], hide_index=True, width="stretch")
        if graphic.status == "unbounded":
            st.warning("Evaluar solo los vértices no basta: existe una dirección factible que mejora el objetivo sin límite.")
        if graphic.rays:
            st.markdown("**Direcciones del cono de recesión**")
            st.dataframe([
                {"d₁": str(d[0]), "d₂": str(d[1]), "Cambio de Z por unidad de t": str(problem.evaluate(d)), "Mejora el objetivo": "Sí" if problem.multiplier * problem.evaluate(d) > 0 else "No"}
                for d in graphic.rays
            ], hide_index=True, width="stretch")
            st.caption("Se exige d ≥ 0 y Aᵢd ≤ 0, ≥ 0 o = 0 según el signo original. Se normaliza d₁ + d₂ = 1. Una dirección con mejora estricta prueba que el objetivo es no acotado.")
    with st.expander("Cómo se calcularon los vértices: todas las intersecciones"):
        st.latex(r"\begin{pmatrix} a_1 & a_2 \\ b_1 & b_2 \end{pmatrix}\begin{pmatrix} x_1 \\ x_2 \end{pmatrix} = \begin{pmatrix} r \\ s \end{pmatrix}")
        st.caption("Se intersectan por parejas las tres fronteras y los dos ejes. Se descartan puntos que incumplen cualquier restricción y se eliminan duplicados. Las igualdades pueden producir segmentos o un único punto factible.")
        st.dataframe([
            {"Fronteras": " ∩ ".join(item.boundaries), "x₁": str(item.point[0]) if item.point else "—", "x₂": str(item.point[1]) if item.point else "—", "Factible": "Sí" if item.feasible else ("No" if item.point is not None else "Sin intersección única")}
            for item in graphic.intersections
        ], hide_index=True, width="stretch")
    st.markdown("**Comparación independiente**")
    st.dataframe([
        {"Método": "Simplex", "Estado": STATUS_LABELS[simplex.status], "Z óptimo": str(simplex.objective_value) if simplex.objective_value is not None else "No hay óptimo finito"},
        {"Método": "Gráfico", "Estado": STATUS_LABELS[graphic.status], "Z óptimo": str(graphic.objective_value) if graphic.objective_value is not None else "No hay óptimo finito"},
    ], hide_index=True, width="stretch")
    if methods_agree(problem, simplex, graphic):
        st.success("Los métodos coinciden en el estado y el valor óptimo. Si hay varios óptimos, pueden seleccionar puntos diferentes.")
    else:
        st.error("Los métodos no coinciden o el simplex se interrumpió. Examine la traza antes de aceptar el resultado.")

with check_tab:
    st.subheader("Verificación con resultados conocidos")
    st.write("Los ejemplos incluyen maximización, minimización, variables artificiales, signos combinados, infactibilidad, no acotación y soluciones múltiples.")
    verifications = verify_examples()
    st.dataframe(verifications, hide_index=True, width="stretch")
    if all(row["Verificación"] == "Correcto" for row in verifications):
        st.success("6 de 6 ejemplos verificados correctamente.")
    st.subheader("Guardar el procedimiento")
    report = build_report(problem, simplex, graphic)
    model_data = {
        "sentido": problem.sense,
        "objetivo": list(map(str, problem.objective)),
        "restricciones": [{"coeficientes": list(map(str, r.coefficients)), "signo": r.sign, "b": str(r.rhs)} for r in problem.constraints],
        "no_negatividad": ["x1 >= 0", "x2 >= 0"],
    }
    report_col, data_col = st.columns(2)
    report_col.download_button("Descargar procedimiento (.md)", report.encode("utf-8"), file_name="procedimiento_programacion_lineal.md", mime="text/markdown", width="stretch")
    data_col.download_button("Descargar datos del modelo (.json)", json.dumps(model_data, indent=2, ensure_ascii=False).encode("utf-8"), file_name="modelo.json", mime="application/json", width="stretch")
    st.caption("El reporte contiene el modelo, la transformación, la tabla inicial, todas las razones, pivotes, operaciones, tablas y la comparación. Los cálculos del solver no dependen de SciPy ni de otro optimizador.")

st.caption("Proyecto académico · Dos variables y tres restricciones · Python + Streamlit + Plotly")
