"""
visuals.py - Styling, Plotly society graph and small HTML helpers for the Streamlit UI.
"""
from __future__ import annotations

import html
import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import plotly.graph_objects as go
import streamlit as st

from graph_data import (BASE_GRAPH, CURVED_EDGES, LOCATION_ICONS, LOCATIONS, NODE_POSITIONS,
                        SHUTTLE_ICON, list_roads, road_key)

NAVY, NAVY_2, PURPLE, PURPLE_D = "#0F1B3D", "#1A2850", "#7B2CBF", "#5A189A"

ROLE_STYLE = {  # fill, border
    "default": ("#FFFFFF", "#1A2850"),
    "current": ("#7B2CBF", "#3C096C"),
    "candidate": ("#FDE68A", "#D97706"),
    "selected": ("#F9A8D4", "#BE185D"),
    "visited": ("#BBF7D0", "#15803D"),
    "processed": ("#E0E7FF", "#6366F1"),
    "target": ("#C7D2FE", "#4338CA"),
    "start": ("#DDD6FE", "#6D28D9"),
}

CSS = f"""
<style>
.stApp {{ background:#EEF2F8; }}
.block-container {{ padding-top:1rem; padding-bottom:3rem; max-width:1450px; }}
[data-testid="stSidebar"] {{ background:{NAVY}; }}
[data-testid="stSidebar"] * {{ color:#E2E8F0; }}
[data-testid="stSidebar"] label p {{ color:#E2E8F0 !important; }}
.hero {{ background:linear-gradient(135deg,{NAVY} 0%,{NAVY_2} 100%); border-radius:14px; padding:20px 28px; margin-bottom:16px; }}
.hero h1 {{ color:#fff; font-size:1.9rem; margin:0; font-weight:800; letter-spacing:-0.3px; }}
.hero p {{ color:#B8C4E0; margin:6px 0 0 0; font-size:0.98rem; }}
.card {{ background:#fff; border:1px solid #D9E0EC; border-radius:12px; padding:16px 18px; margin-bottom:12px; }}
.card h4 {{ margin:0 0 8px 0; color:{PURPLE_D}; font-size:1.05rem; }}
.card.accent {{ border:2px solid {PURPLE}; }}
.recurrence {{ background:{PURPLE}; color:#fff; border-radius:12px; padding:16px 20px; font-family:Consolas,'Courier New',monospace; font-size:0.98rem; line-height:1.75; }}
.recurrence b {{ color:#F5D0FE; font-family:'Segoe UI',sans-serif; }}
.pseudo {{ background:#0B1330; color:#E2E8F0; border-radius:10px; padding:10px 0; font-family:Consolas,'Courier New',monospace; font-size:0.88rem; }}
.pseudo div {{ padding:3px 16px; white-space:pre-wrap; }}
.pseudo div.on {{ background:{PURPLE}; color:#fff; font-weight:700; }}
.badge {{ display:inline-block; background:{PURPLE}; color:#fff; border-radius:999px; padding:3px 14px; font-weight:700; font-size:0.85rem; }}
.pill {{ display:inline-block; border-radius:999px; padding:2px 10px; font-size:0.8rem; font-weight:600; margin:0 4px 4px 0; }}
.metric {{ background:#fff; border:1px solid #D9E0EC; border-radius:12px; padding:12px 14px; height:100%; }}
.metric .v {{ font-size:1.4rem; font-weight:800; color:{NAVY}; }}
.metric .l {{ font-size:0.8rem; color:#64748B; }}
.tbl-wrap {{ overflow-x:auto; }}
table.t {{ border-collapse:collapse; width:100%; font-size:0.88rem; }}
table.t th {{ background:#F1F5F9; color:{NAVY}; padding:6px 10px; border:1px solid #D9E0EC; text-align:center; }}
table.t td {{ padding:5px 10px; border:1px solid #E2E8F0; text-align:center; background:#fff; }}
table.t td.rowh {{ background:#F1F5F9; font-weight:700; text-align:left; }}
table.t td.cand {{ background:#FEF3C7; font-weight:700; }}
table.t td.sel {{ background:#FBCFE8; font-weight:700; }}
table.t td.cur {{ background:#DDD6FE; font-weight:700; }}
table.t tr.hl td {{ background:#EDE9FE; font-weight:700; }}
table.t tr.best td {{ background:#FBCFE8; font-weight:700; }}
table.t td.pass {{ background:#DCFCE7; color:#166534; font-weight:700; }}
table.t td.fail {{ background:#FEE2E2; color:#991B1B; font-weight:700; }}
table.t td.diag {{ background:#F1F5F9; color:#94A3B8; }}
.flow {{ display:flex; flex-wrap:wrap; align-items:center; gap:6px; }}
.flow .box {{ background:#fff; border:1.5px solid {PURPLE}; color:{NAVY}; border-radius:10px; padding:8px 12px; font-size:0.85rem; font-weight:600; }}
.flow .arrow {{ color:{PURPLE}; font-weight:800; font-size:1.2rem; }}
.note {{ background:#FEF3C7; border:1px solid #F59E0B; color:#78350F; border-radius:10px; padding:10px 14px; font-size:0.9rem; }}
.legend span {{ display:inline-block; margin-right:14px; font-size:0.82rem; color:#334155; }}
.legend i {{ display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:5px; vertical-align:-1px; border:2px solid; }}
.stButton>button[kind="primary"], button[data-testid="stBaseButton-primary"], [data-testid="stFormSubmitButton"] button {{
  background:{PURPLE}; border-color:{PURPLE}; color:#fff; font-weight:700; }}
.stButton>button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {{ background:{PURPLE_D}; border-color:{PURPLE_D}; }}
.stButton>button[kind="secondary"], button[data-testid="stBaseButton-secondary"] {{ border:1.5px solid {PURPLE}; color:{PURPLE_D}; font-weight:600; background:#fff; }}
h2, h3 {{ color:{NAVY}; }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def card(inner_html: str, title: str = "", accent: bool = False) -> None:
    head = f"<h4>{title}</h4>" if title else ""
    st.markdown(f'<div class="card{" accent" if accent else ""}">{head}{inner_html}</div>', unsafe_allow_html=True)


def metric(label: str, value: str) -> str:
    return f'<div class="metric"><div class="v">{html.escape(value)}</div><div class="l">{html.escape(label)}</div></div>'


def fmt_cost(x: Optional[float], unavailable: str = "—") -> str:
    """Display-friendly cost: never shows 'inf' or 'nan'."""
    if x is None or isinstance(x, str) or not math.isfinite(x):
        return unavailable
    return f"{x:.2f}".rstrip("0").rstrip(".")


def html_table(headers: Sequence[str], rows: Sequence[Sequence[str]],
               cell_cls: Optional[Dict[Tuple[int, int], str]] = None,
               row_cls: Optional[Dict[int, str]] = None, first_col_header: bool = False) -> str:
    cell_cls, row_cls = cell_cls or {}, row_cls or {}
    out = ['<div class="tbl-wrap"><table class="t"><thead><tr>']
    out += [f"<th>{html.escape(str(h))}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for r, row in enumerate(rows):
        out.append(f'<tr class="{row_cls.get(r, "")}">')
        for c, val in enumerate(row):
            cls = cell_cls.get((r, c), "")
            if first_col_header and c == 0:
                cls = (cls + " rowh").strip()
            out.append(f'<td class="{cls}">{html.escape(str(val))}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def pseudocode_html(lines: Sequence[str], active: Optional[int]) -> str:
    """active = 1-based numbered line (for TSP lines 1-8; Dijkstra uses the same convention)."""
    parts = ['<div class="pseudo">']
    for k, text in enumerate(lines, start=1):
        parts.append(f'<div class="{"on" if k == active else ""}">{html.escape(text)}</div>')
    parts.append("</div>")
    return "".join(parts)


def legend_html(items: Iterable[str]) -> str:
    names = {"current": "current", "candidate": "candidate", "selected": "selected / minimum",
             "visited": "finalised", "processed": "already processed", "target": "terminal"}
    spans = []
    for key in items:
        fill, border = ROLE_STYLE[key]
        spans.append(f'<span><i style="background:{fill};border-color:{border}"></i>{names[key]}</span>')
    spans.append(f'<span><i style="background:{PURPLE};border-color:{PURPLE}"></i>final route</span>')
    spans.append('<span><i style="background:#fff;border-color:#DC2626"></i>blocked road</span>')
    return '<div class="legend">' + "".join(spans) + "</div>"


def edge_points(a: str, b: str, steps: int = 21) -> List[Tuple[float, float]]:
    """Points from a to b along the (possibly curved) road."""
    (x0, y0), (x1, y1) = NODE_POSITIONS[a], NODE_POSITIONS[b]
    ctrl = CURVED_EDGES.get(road_key(a, b))
    pts = []
    for k in range(steps):
        t = k / (steps - 1)
        if ctrl is None:
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        else:  # quadratic Bezier; control point is defined for the stored direction, symmetric anyway
            pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * ctrl[0] + t ** 2 * x1,
                        (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ctrl[1] + t ** 2 * y1))
    return pts


def _path_edges(path: Optional[Sequence[str]]) -> List[Tuple[str, str]]:
    return list(zip(path, path[1:])) if path and len(path) > 1 else []


def build_graph_figure(graph: Dict[str, Dict[str, float]], *, roles: Optional[Dict[str, str]] = None,
                       route_paths: Sequence[Sequence[str]] = (), selected_paths: Sequence[Sequence[str]] = (),
                       candidate_paths: Sequence[Sequence[str]] = (), relaxed_edge: Optional[Tuple[str, str]] = None,
                       shuttle_at: Optional[str] = None, blocked: Sequence[Tuple[str, str]] = (),
                       outlined: Sequence[str] = (), height: int = 470) -> go.Figure:
    roles = roles or {}
    blocked_keys = {road_key(a, b) for a, b in blocked}
    fig = go.Figure()
    annotations = []

    for a, b, _w in list_roads(BASE_GRAPH):
        pts = edge_points(a, b)
        is_blocked = road_key(a, b) in blocked_keys
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", hoverinfo="skip",
                                 showlegend=False,
                                 line=dict(color="#DC2626" if is_blocked else "#94A3B8",
                                           width=2 if is_blocked else 1.6, dash="dash" if is_blocked else "solid")))
        mx, my = pts[len(pts) // 2]
        label = "✕ blocked" if is_blocked else fmt_cost(graph.get(a, {}).get(b))
        annotations.append(dict(x=mx, y=my, text=f"<b>{label}</b>", showarrow=False, font=dict(size=11, color="#B91C1C" if is_blocked else "#334155"),
                                bgcolor="#FFFFFF", bordercolor="#CBD5E1", borderwidth=1, borderpad=2, opacity=0.95))

    def draw(paths, color, width, arrows):
        for path in paths:
            for a, b in _path_edges(path):
                pts = edge_points(a, b)
                fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="lines", hoverinfo="skip",
                                         showlegend=False, line=dict(color=color, width=width)))
                if arrows:
                    k = len(pts) // 2 + 2
                    annotations.append(dict(x=pts[k][0], y=pts[k][1], ax=pts[k - 2][0], ay=pts[k - 2][1], xref="x", yref="y",
                                            axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4,
                                            arrowwidth=2, arrowcolor=color, text=""))

    draw(candidate_paths, "#C4B5FD", 5, False)
    draw(route_paths, PURPLE, 7, True)
    draw(selected_paths, "#DB2777", 7, True)
    if relaxed_edge:
        draw([list(relaxed_edge)], "#F97316", 6, True)

    xs, ys, fills, borders, widths, names, hover = [], [], [], [], [], [], []
    for name in LOCATIONS:
        x, y = NODE_POSITIONS[name]
        fill, border = ROLE_STYLE.get(roles.get(name, "default"))
        xs.append(x); ys.append(y); fills.append(fill); borders.append(border)
        widths.append(4 if name in outlined else 2); names.append(f"<b>{name}</b>")
        hover.append(f"{name}")
        annotations.append(dict(x=x, y=y, text=LOCATION_ICONS[name], showarrow=False, font=dict(size=20)))
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=names, textposition="bottom center",
                             textfont=dict(size=12, color="#0F1B3D"), hovertext=hover, hoverinfo="text",
                             showlegend=False,
                             marker=dict(size=40, color=fills, line=dict(color=borders, width=widths))))

    if shuttle_at in NODE_POSITIONS:
        x, y = NODE_POSITIONS[shuttle_at]
        annotations.append(dict(x=x, y=y, yshift=36, text=SHUTTLE_ICON, showarrow=False, font=dict(size=24),
                                bgcolor="#FFFFFF", bordercolor=PURPLE, borderwidth=2, borderpad=3))

    fig.update_layout(annotations=annotations, height=height, margin=dict(l=4, r=4, t=8, b=4),
                      paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      xaxis=dict(visible=False, range=[-1.0, 11.8], fixedrange=True),
                      yaxis=dict(visible=False, range=[-2.4, 6.3], fixedrange=True))
    return fig

def _route_polyline(route: Sequence[str]) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    for a, b in zip(route, route[1:]):
        seg = edge_points(a, b, steps=41)
        pts.extend(seg if not pts else seg[1:])
    return pts


def _resample(pts: List[Tuple[float, float]], max_frames: int = 320, min_step: float = 0.08):
    """Points at equal distance along the polyline => constant shuttle speed, also through curves."""
    cum = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(x1 - x0, y1 - y0))
    total = cum[-1]
    step = max(min_step, total / max_frames)
    n = max(2, int(total / step) + 1)
    out, k = [], 0
    for q in range(n + 1):
        d = min(total, q * total / n)
        while k < len(cum) - 2 and cum[k + 1] < d:
            k += 1
        seg = cum[k + 1] - cum[k]
        t = 0.0 if seg == 0 else (d - cum[k]) / seg
        out.append((pts[k][0] + (pts[k + 1][0] - pts[k][0]) * t, pts[k][1] + (pts[k + 1][1] - pts[k][1]) * t))
    return out


def build_animated_route_figure(graph, route: Sequence[str], outlined=(), frame_ms: int = 30,
                                height: int = 440) -> go.Figure:
    """Graph with the final route; a bus glides along it in one continuous motion when Drive is pressed."""
    fig = build_graph_figure(graph, route_paths=[route], outlined=list(outlined),
                             roles={route[0]: "start", route[-1]: "target"}, height=height)
    path = _resample(_route_polyline(route))
    shuttle_idx = len(fig.data)
    fig.add_trace(go.Scatter(x=[path[0][0]], y=[path[0][1]], mode="text", text=[SHUTTLE_ICON],
                             textfont=dict(size=30), hoverinfo="skip", showlegend=False))
    trail_idx = len(fig.data)
    fig.add_trace(go.Scatter(x=[path[0][0]], y=[path[0][1]], mode="lines", hoverinfo="skip", showlegend=False,
                             line=dict(color="#F59E0B", width=4)))
    xs, ys = [p[0] for p in path], [p[1] for p in path]
    fig.frames = [go.Frame(name=str(k), traces=[shuttle_idx, trail_idx],
                           data=[go.Scatter(x=[xs[k]], y=[ys[k]]), go.Scatter(x=xs[: k + 1], y=ys[: k + 1])])
                  for k in range(len(path))]
    play = dict(frame=dict(duration=frame_ms, redraw=False), transition=dict(duration=0), fromcurrent=True, mode="immediate")
    reset = dict(frame=dict(duration=0, redraw=False), transition=dict(duration=0), mode="immediate")
    fig.update_layout(updatemenus=[dict(type="buttons", direction="left", x=0.01, y=0.99, xanchor="left", yanchor="top",
                                        pad=dict(r=4, t=4), bgcolor="#7B2CBF", bordercolor="#5A189A",
                                        font=dict(color="#FFFFFF", size=13), showactive=False,
                                        buttons=[dict(label="▶ Drive shuttle", method="animate", args=[None, play]),
                                                 dict(label="⏸ Pause", method="animate", args=[[None], reset]),
                                                 dict(label="⏮ Back to start", method="animate", args=[["0"], reset])])])
    return fig

_FOOTPRINTS = {
    "Main Gate": (1.1, 0.7, "#DDD6FE", "#6D28D9"),
    "Block A": (1.5, 0.95, "#CBD5E1", "#64748B"),
    "Block B": (1.5, 0.95, "#CBD5E1", "#64748B"),
    "Block C": (1.5, 0.95, "#CBD5E1", "#64748B"),
    "Market": (1.7, 1.0, "#FED7AA", "#EA580C"),
    "Hospital": (1.7, 1.1, "#FECACA", "#DC2626"),
    "School": (1.7, 1.1, "#FEF08A", "#CA8A04"),
    "Temple": (1.4, 1.1, "#FBCFA0", "#C2410C"),
    "Metro Station": (1.9, 1.0, "#C7D2FE", "#4338CA"),
}
_TREES = [(0.6, 4.9), (3.4, 5.9), (7.6, 4.9), (9.4, 2.3), (0.5, 0.3), (4.3, 0.9), (9.5, 0.2), (7.8, 6.2), (10.9, 6.1)]

_MAP_POS = dict(NODE_POSITIONS)
_MAP_POS.update({"School": (11.4, 3.2), "Temple": (13.2, 4.3), "Metro Station": (12.9, 1.0)})
_MAP_CURVE = {frozenset({"Main Gate", "Metro Station"}): (4.5, -3.2)}
_BOUNDARY = [(-1.0, -1.15), (7.6, -1.15), (7.6, 4.0), (10.15, 4.0), (10.15, 6.9), (-1.0, 6.9)]


def _map_edge_points(a: str, b: str, steps: int = 41) -> List[Tuple[float, float]]:
    (x0, y0), (x1, y1) = _MAP_POS[a], _MAP_POS[b]
    ctrl = _MAP_CURVE.get(road_key(a, b))
    pts = []
    for k in range(steps):
        t = k / (steps - 1)
        if ctrl is None:
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t))
        else:
            pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * ctrl[0] + t ** 2 * x1,
                        (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ctrl[1] + t ** 2 * y1))
    return pts


def _inside_boundary(x: float, y: float) -> bool:
    inside = False
    n = len(_BOUNDARY)
    for k in range(n):
        (x0, y0), (x1, y1) = _BOUNDARY[k], _BOUNDARY[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def _back_gates() -> List[Tuple[float, float, int, int]]:
    """Where each road crosses the society boundary: (x, y, label x-shift, label y-shift)."""
    gates = []
    for a, b, _w in list_roads(BASE_GRAPH):
        pts = _map_edge_points(a, b, 401)
        for p, q in zip(pts, pts[1:]):
            if _inside_boundary(*p) != _inside_boundary(*q):
                x, y = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                on_vertical_wall = min(abs(x - 7.6), abs(x + 1.0), abs(x - 10.15)) < 0.08
                label_up = on_vertical_wall and abs(x - 10.15) < 0.08 and y > 4.6   # keep the two labels apart
                gates.append((x, y, 0, 24 if label_up else -24) if on_vertical_wall else (x, y, 46, 0))
                break
    return gates


def build_map_figure(height: int = 540) -> go.Figure:
    fig = go.Figure()
    shapes, annotations = [], []

    path = "M " + " L ".join(f"{x},{y}" for x, y in _BOUNDARY) + " Z"
    shapes.append(dict(type="path", layer="below", fillcolor="#E6F2DD", line=dict(color="#7BA05B", width=3), path=path))

    for a, b, _w in list_roads(BASE_GRAPH):
        pts = _map_edge_points(a, b)
        x, y = [p[0] for p in pts], [p[1] for p in pts]
        for width, color, dash in ((17, "#C9CFD9", "solid"), (13, "#5B6472", "solid"), (1.6, "#F8FAFC", "dash")):
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", hoverinfo="skip", showlegend=False,
                                     line=dict(color=color, width=width, dash=dash)))

    for name in LOCATIONS:
        cx, cy = _MAP_POS[name]
        if name in _FOOTPRINTS:
            w, h, fill, border = _FOOTPRINTS[name]
            shapes.append(dict(type="rect", x0=cx - w / 2, x1=cx + w / 2, y0=cy - h / 2, y1=cy + h / 2,
                               fillcolor=fill, line=dict(color=border, width=2.5)))
            shapes.append(dict(type="rect", x0=cx - w / 2 + 0.1, x1=cx + w / 2 - 0.1, y0=cy - h / 2 + 0.1, y1=cy + h / 2 - 0.1,
                               fillcolor="rgba(255,255,255,0.35)", line=dict(color=border, width=1, dash="dot")))
            label_y = cy - h / 2 - 0.2
        else:  
            shapes.append(dict(type="circle", x0=cx - 0.34, x1=cx + 0.34, y0=cy - 0.34, y1=cy + 0.34,
                               fillcolor="#5B6472", line=dict(color="#C9CFD9", width=3)))
            shapes.append(dict(type="circle", x0=cx - 0.15, x1=cx + 0.15, y0=cy - 0.15, y1=cy + 0.15,
                               fillcolor="#86EFAC", line=dict(color="#15803D", width=1.5)))
            label_y = cy - 0.55
        annotations.append(dict(x=cx, y=cy, text=LOCATION_ICONS[name], showarrow=False, font=dict(size=24 if name in _FOOTPRINTS else 16)))
        annotations.append(dict(x=cx, y=label_y, text=f"<b>{name}</b>", showarrow=False, font=dict(size=12, color="#0F1B3D"),
                                bgcolor="rgba(255,255,255,0.85)", borderpad=2))

    for tx, ty in _TREES:
        annotations.append(dict(x=tx, y=ty, text="🌳", showarrow=False, font=dict(size=22)))

    gx, gy = _MAP_POS["Main Gate"]
    annotations.append(dict(x=gx, y=gy, yshift=34, text=SHUTTLE_ICON, showarrow=False, font=dict(size=22)))
    annotations.append(dict(x=14.2, y=5.35, ax=14.2, ay=6.15, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                            arrowhead=2, arrowwidth=3, arrowcolor="#0F1B3D", text=""))
    annotations.append(dict(x=14.2, y=6.35, text="<b>N</b>", showarrow=False, font=dict(size=14, color="#0F1B3D")))
    annotations.append(dict(x=-0.9, y=-1.0, xanchor="left", yanchor="bottom", showarrow=False,
                            text="<b>Society Shuttle Plan</b>",
                            font=dict(size=11, color="#334155"), bgcolor="rgba(255,255,255,0.8)", borderpad=3))
    annotations.append(dict(x=-0.9, y=6.75, xanchor="left", yanchor="top", showarrow=False, text="<b>Society boundary</b>",
                            font=dict(size=11, color="#3F6212")))
    annotations.append(dict(x=13.6, y=2.4, showarrow=False, text="<i>Outside the society</i>", font=dict(size=11, color="#475569")))

    for gx_, gy_, dx_, dy_ in _back_gates():
        annotations.append(dict(x=gx_, y=gy_, text="🚧", showarrow=False, font=dict(size=20)))
        annotations.append(dict(x=gx_, y=gy_, xshift=dx_, yshift=dy_, text="<b>Back gate</b>", showarrow=False,
                                font=dict(size=10, color="#7C2D12"), bgcolor="rgba(255,237,213,0.95)",
                                bordercolor="#EA580C", borderwidth=1, borderpad=2))

    fig.add_trace(go.Scatter(x=[_MAP_POS[n][0] for n in LOCATIONS], y=[_MAP_POS[n][1] for n in LOCATIONS],
                             mode="markers", marker=dict(size=34, opacity=0), hovertext=LOCATIONS, hoverinfo="text",
                             showlegend=False))
    fig.update_layout(shapes=shapes, annotations=annotations, height=height, margin=dict(l=4, r=4, t=8, b=4),
                      paper_bgcolor="#FFFFFF", plot_bgcolor="#F1F5F9",
                      xaxis=dict(visible=False, range=[-1.1, 14.9], fixedrange=True),
                      yaxis=dict(visible=False, range=[-1.25, 7.1], fixedrange=True, scaleanchor="x", scaleratio=1))
    return fig