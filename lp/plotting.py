"""Gráfica interactiva. Los float se usan únicamente para dibujar."""

from fractions import Fraction

import plotly.graph_objects as go

from .geometry import GraphicResult, clip_line, convex_hull, visible_region
from .model import LPProblem, Point, parse_number
from .presentation import SIGN_TEXT

COLORS = ("#3875BD", "#D78A26", "#9B5FC0")


def default_limits(graphic: GraphicResult) -> tuple[float, float]:
    xmax = max((v[0] for v in graphic.vertices), default=Fraction(0))
    ymax = max((v[1] for v in graphic.vertices), default=Fraction(0))
    return float(max(Fraction(5), xmax * Fraction(5, 4))), float(max(Fraction(5), ymax * Fraction(5, 4)))


def _coords(points):
    return [float(p[0]) for p in points], [float(p[1]) for p in points]


def _ray_segment(anchor: Point, direction: Point, xmax: Fraction, ymax: Fraction):
    if not (0 <= anchor[0] < xmax and 0 <= anchor[1] < ymax):
        return ()
    times = [(limit - x) / d for limit, x, d in zip((xmax, ymax), anchor, direction) if d > 0]
    if not times:
        return ()
    t = min(times) * Fraction(9, 10)
    return anchor, (anchor[0] + t * direction[0], anchor[1] + t * direction[1])


def build_figure(problem: LPProblem, graphic: GraphicResult, xmax, ymax) -> go.Figure:
    xmax, ymax = parse_number(xmax), parse_number(ymax)
    if xmax <= 0 or ymax <= 0:
        raise ValueError("Los límites de la ventana deben ser positivos.")
    fig = go.Figure()
    region = visible_region(problem, xmax, ymax)
    if region:
        closed = (*region, region[0]) if len(region) >= 3 else region
        x, y = _coords(closed)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines" if len(region) >= 2 else "markers",
            fill="toself" if len(region) >= 3 else None,
            fillcolor="rgba(22,107,87,0.16)", line=dict(color="#5DA58D", width=6 if len(region) == 2 else 1),
            marker=dict(size=13, color="#166B57"),
            name="Región factible" + (" (recorte)" if graphic.rays else ""),
            hoverinfo="name",
        ))

    for i, row in enumerate(problem.constraints):
        if not any(row.coefficients):
            continue
        points = clip_line(row.coefficients, row.rhs, xmax, ymax)
        x, y = _coords(points)
        equation = f"{row.coefficients[0]} x₁ + ({row.coefficients[1]}) x₂ {SIGN_TEXT[row.sign]} {row.rhs}"
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines" if len(points) >= 2 else "markers",
            line=dict(color=COLORS[i], width=2.5, dash="solid" if row.sign == "=" else "dash"),
            name=f"R{i+1} · {SIGN_TEXT[row.sign]}", hovertemplate=equation + "<extra></extra>",
        ))

    if graphic.objective_value is not None and any(problem.objective):
        points = clip_line(problem.objective, graphic.objective_value, xmax, ymax)
        x, y = _coords(points)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", line=dict(color="#D34E55", width=2, dash="dot"),
            name=f"Objetivo · Z = {graphic.objective_value}",
            hovertemplate=f"Recta de nivel óptimo: Z = {graphic.objective_value}<extra></extra>",
        ))

    if graphic.vertices:
        ray_legends = set()
        for i, direction in enumerate(graphic.rays):
            optimal_ray = graphic.status == "optimal" and problem.evaluate(direction) == 0
            anchor = graphic.optimal_vertices[0] if optimal_ray else graphic.vertices[0]
            points = _ray_segment(anchor, direction, xmax, ymax)
            if not points:
                continue
            x, y = _coords(points)
            improving = problem.multiplier * problem.evaluate(direction) > 0
            color = "#166B57" if optimal_ray else ("#D34E55" if improving else "#75847E")
            label = "Rayo óptimo" if optimal_ray else ("Dirección de mejora" if improving else "Dirección no acotada")
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", line=dict(color=color, width=2, dash="dashdot"),
                name=label,
                legendgroup=label, showlegend=label not in ray_legends,
                hovertemplate=f"d = ({direction[0]}, {direction[1]}); cambio de Z = {problem.evaluate(direction)}<extra></extra>",
            ))
            ray_legends.add(label)
            fig.add_annotation(x=x[-1], y=y[-1], ax=x[0], ay=y[0], xref="x", yref="y", axref="x", ayref="y", text="", showarrow=True, arrowhead=3, arrowcolor=color, arrowsize=1.3)

    if graphic.vertices:
        x, y = _coords(graphic.vertices)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers+text", marker=dict(color="#253F38", size=9, line=dict(color="white", width=1)),
            text=[f"V{i+1}" for i in range(len(graphic.vertices))], textposition="top right", name="Vértices factibles",
            customdata=[[str(v[0]), str(v[1]), str(z)] for v, z in zip(graphic.vertices, graphic.vertex_values)],
            hovertemplate="x₁ = %{customdata[0]}<br>x₂ = %{customdata[1]}<br>Z = %{customdata[2]}<extra></extra>",
        ))
    if graphic.optimal_vertices:
        optimal_hull = convex_hull(graphic.optimal_vertices)
        if len(optimal_hull) >= 2:
            points = (*optimal_hull, optimal_hull[0]) if len(optimal_hull) > 2 else optimal_hull
            x, y = _coords(points)
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", line=dict(color="#166B57", width=5),
                name="Conjunto de óptimos" if len(optimal_hull) > 2 else "Segmento óptimo", hoverinfo="name",
            ))
        x, y = _coords(graphic.optimal_vertices)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers", marker=dict(symbol="star", size=19, color="#166B57", line=dict(color="white", width=1.5)),
            name="Óptimo", hovertemplate="Óptimo: (%{x}, %{y})<extra></extra>",
        ))

    fig.update_layout(
        height=560, margin=dict(l=25, r=25, t=25, b=70),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, sans-serif", color="#253F38", size=13),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
        hovermode="closest", dragmode="pan",
        xaxis=dict(title="x₁", range=[0, float(xmax)], gridcolor="#E6ECE8", zerolinecolor="#9BAFA4"),
        yaxis=dict(title="x₂", range=[0, float(ymax)], gridcolor="#E6ECE8", zerolinecolor="#9BAFA4"),
        uirevision=f"{problem!r}:{xmax}:{ymax}",
    )
    return fig
