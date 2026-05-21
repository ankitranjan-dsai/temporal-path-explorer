# Credit: A.
# Integrated from: none (app-specific); added for main Plotly UI.
# Role: Spring layout and cumulative-time-t Plotly network (Explore / Analyze / Advanced).

from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

_CANONICAL = {"SRC", "TGT", "Unix", "edge_id"}


def _ensure_canonical(df: pd.DataFrame) -> None:
    miss = _CANONICAL - set(df.columns)
    if miss:
        raise ValueError(f"DataFrame must have columns {sorted(_CANONICAL)}; missing {sorted(miss)}")


def compute_spring_positions(df: pd.DataFrame, *, seed: int = 42) -> Dict[str, Tuple[float, float]]:
    _ensure_canonical(df)
    G = nx.DiGraph()
    for _, row in df.iterrows():
        u = str(row["SRC"]).strip()
        v = str(row["TGT"]).strip()
        G.add_edge(u, v)
    pos = nx.spring_layout(G, seed=seed)
    return {str(k): (float(v[0]), float(v[1])) for k, v in pos.items()}


def _axis_ranges_from_pos(
    pos: Dict[str, Tuple[float, float]], *, pad_ratio: float = 0.12
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Full-graph node bounding box + padding so the view does not auto-zoom to the visible subgraph only."""
    coords = list(pos.values())
    if not coords:
        return (-1.0, 1.0), (-1.0, 1.0)
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    dx = max(xmax - xmin, 1e-9)
    dy = max(ymax - ymin, 1e-9)
    px = pad_ratio * dx
    py = pad_ratio * dy
    return (xmin - px, xmax + px), (ymin - py, ymax + py)


def _axes_fixed_from_pos(pos: Dict[str, Tuple[float, float]]) -> Tuple[dict, dict]:
    (x0, x1), (y0, y1) = _axis_ranges_from_pos(pos)
    base = dict(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        visible=False,
        autorange=False,
    )
    xaxis = {**base, "range": [x0, x1]}
    yaxis = {**base, "range": [y0, y1], "scaleanchor": "x", "scaleratio": 1}
    return xaxis, yaxis


def temporal_network_figure(
    df: pd.DataFrame,
    t_cutoff: int,
    pos: Dict[str, Tuple[float, float]],
    *,
    path_edge_ids: Optional[Set[str]] = None,
    stress_edge_ids: Optional[Set[str]] = None,
    stress_vertices: Optional[Set[str]] = None,
    whatif_edge_ids: Optional[Set[str]] = None,
    whatif_vertices: Optional[Set[str]] = None,
    max_edges_draw: int = 1200,
    plot_title: Optional[str] = None,
    figure_height: Optional[int] = None,
) -> Tuple[go.Figure, Optional[str]]:
    """
    Cumulative view: edges with Unix <= t_cutoff only.
    path_edge_ids / stress_edge_ids: highlight edges; stress_vertices: highlight nodes (yellow tones, bottleneck tab).
    whatif_edge_ids / whatif_vertices: What-if removals (Analyze); orange emphasis on edges/nodes.
    plot_title: optional in-figure title; default None (prefer Streamlit caption).
    figure_height: override default height in pixels (e.g. larger Advanced tab).
    """
    _ensure_canonical(df)
    xaxis_fixed, yaxis_fixed = _axes_fixed_from_pos(pos)
    path_edge_ids = {str(x) for x in (path_edge_ids or set())}
    stress_edge_ids = {str(x) for x in (stress_edge_ids or set())}
    stress_vertices = {str(x) for x in (stress_vertices or set())}
    whatif_edge_ids = {str(x) for x in (whatif_edge_ids or set())}
    whatif_vertices = {str(x) for x in (whatif_vertices or set())}
    bottleneck_view = bool(stress_edge_ids or stress_vertices)
    h_empty = figure_height if figure_height is not None else 420
    h_main = figure_height if figure_height is not None else 520

    sub = df[df["Unix"] <= t_cutoff].copy()
    warn = None
    if len(sub) > max_edges_draw:
        sub = sub.sample(n=max_edges_draw, random_state=42)
        warn = f"Many edges: plot shows a random sample of up to {max_edges_draw} (full data still used in algorithms)."

    segs_normal: list = []
    segs_stress: list = []
    segs_path: list = []
    segs_whatif: list = []
    for _, row in sub.iterrows():
        u = str(row["SRC"]).strip()
        v = str(row["TGT"]).strip()
        eid = str(row["edge_id"])
        if u not in pos or v not in pos:
            continue
        p0, p1 = pos[u], pos[v]
        item = (p0, p1)
        if eid in path_edge_ids:
            segs_path.append(item)
        elif eid in stress_edge_ids:
            segs_stress.append(item)
        elif eid in whatif_edge_ids:
            segs_whatif.append(item)
        else:
            segs_normal.append(item)

    def _xy(segs: list) -> Tuple[list, list]:
        xs: list = []
        ys: list = []
        for (x0, y0), (x1, y1) in segs:
            xs += [x0, x1, None]
            ys += [y0, y1, None]
        return xs, ys

    fig = go.Figure()
    xs, ys = _xy(segs_normal)
    if xs:
        if bottleneck_view:
            nl = dict(color="rgba(88,88,88,0.22)", width=1)
        else:
            nl = dict(color="rgba(100,100,100,0.35)", width=1)
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=nl,
                hoverinfo="skip",
                name="Edges",
                showlegend=True,
            )
        )
    xs, ys = _xy(segs_whatif)
    if xs:
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="#d35400", width=4),
                hoverinfo="skip",
                name="What-if remove",
                showlegend=True,
            )
        )
    xs, ys = _xy(segs_stress)
    if xs:
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="#d4a017", width=4 if bottleneck_view else 3),
                hoverinfo="skip",
                name="Critical edges",
                showlegend=True,
            )
        )
    xs, ys = _xy(segs_path)
    if xs:
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line=dict(color="#c0392b", width=4),
                hoverinfo="skip",
                name="Earliest path",
                showlegend=True,
            )
        )

    active = set(sub["SRC"].astype(str).str.strip()).union(set(sub["TGT"].astype(str).str.strip()))
    node_list = sorted(active, key=str)
    if not node_list:
        _layout = dict(
            showlegend=True,
            margin=dict(l=8, r=8, t=16, b=8),
            xaxis=xaxis_fixed,
            yaxis=yaxis_fixed,
            plot_bgcolor="#fafafa",
            height=h_empty,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        if plot_title:
            _layout["title"] = plot_title
        fig.update_layout(**_layout)
        return fig, warn

    n_xs = [pos[n][0] for n in node_list if n in pos]
    n_ys = [pos[n][1] for n in node_list if n in pos]
    node_list = [n for n in node_list if n in pos]
    show_labels = len(node_list) < 45
    marker_size = []
    marker_color = []
    for n in node_list:
        if n in stress_vertices:
            marker_size.append(22 if bottleneck_view else 20)
            marker_color.append("#f1c40f" if bottleneck_view else "#e67e22")
        elif n in whatif_vertices:
            marker_size.append(18)
            marker_color.append("#e67e22")
        else:
            marker_size.append(9 if bottleneck_view else 11)
            marker_color.append("#3498db")

    fig.add_trace(
        go.Scatter(
            x=n_xs,
            y=n_ys,
            mode="markers+text" if show_labels else "markers",
            marker=dict(size=marker_size, color=marker_color, line=dict(width=1, color="#2c3e50")),
            text=node_list if show_labels else None,
            textposition="top center",
            textfont=dict(size=10 if bottleneck_view and show_labels else 9),
            name="Nodes",
            customdata=node_list,
            hovertemplate="<b>%{customdata}</b><extra></extra>",
        )
    )

    _layout_main = dict(
        showlegend=True,
        margin=dict(l=8, r=8, t=24 if not plot_title else 48, b=8),
        xaxis=xaxis_fixed,
        yaxis=yaxis_fixed,
        plot_bgcolor="#fafafa",
        height=h_main,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    if plot_title:
        _layout_main["title"] = plot_title
    fig.update_layout(**_layout_main)
    return fig, warn


__all__ = ["compute_spring_positions", "temporal_network_figure"]
