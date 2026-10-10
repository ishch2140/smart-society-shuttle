"""
app.py - Smart Society Shuttle: Interactive Dynamic Programming and Routing
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

import visuals as vz
from algorithms import (DIJKSTRA_PSEUDOCODE, INF, MODE_METRO, MODE_TEXTBOOK, RouteError, dijkstra,
                        expected_states, run_scaling_experiment, solve_route, tsp_pseudocode)
from graph_data import (BASE_GRAPH, COST_UNIT, LOCATION_ICONS, LOCATIONS, SHUTTLE_ICON, TRAFFIC_MULTIPLIERS,
                        apply_conditions, list_roads, road_label)
from test_cases import TEST_CATALOG, run_all_tests

st.set_page_config(page_title="Smart Society Shuttle - DP & Routing Lab", page_icon="🚌", layout="wide")
vz.inject_css()
ss = st.session_state

PAGES = ["🏠 Overview", "🧭 Dijkstra Routing", "🚌 Multi-Stop TSP", "✅ Test Cases",
         "⏱️ Performance & Complexity", "⚖️ Algorithm Comparison", "📘 Project Methodology"]
ROAD_OPTIONS = {road_label(a, b): (a, b) for a, b, _ in list_roads()}
SPEEDS = {"Slow": 1.6, "Medium": 0.8, "Fast": 0.25}
KIND_TITLES = {"base": "Base case", "state": "Recurrence state", "final": "Final answer g(1, …)",
               "return": "Return the answer", "reconstruct": "Reconstruct the tour"}


def tag(name: str) -> str:
    return f"{LOCATION_ICONS[name]} {name}"


def show_fig(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, key=key)


def set_str(cities: List[int]) -> str:
    return "{" + ", ".join(str(c + 1) for c in cities) + "}" if cities else "∅"

def condition_inputs(prefix: str, container, default_traffic="Normal", default_blocked=()):
    traffic = container.selectbox("Traffic condition", list(TRAFFIC_MULTIPLIERS),
                                  index=list(TRAFFIC_MULTIPLIERS).index(default_traffic), key=f"{prefix}_traffic",
                                  help="Multiplies every road cost: Normal ×1.0, Morning Peak ×1.35, Evening Peak ×1.5")
    labels = container.multiselect("Blocked roads (both directions)", list(ROAD_OPTIONS), default=list(default_blocked),
                                   key=f"{prefix}_blocked")
    return traffic, [ROAD_OPTIONS[l] for l in labels]

def _move(prefix: str, action: str, last: int) -> None:
    key = f"{prefix}_step"
    cur = ss.get(key, 0)
    new = {"first": 0, "prev": cur - 1, "next": cur + 1, "last": last}[action]
    ss[key] = max(0, min(last, new))
    ss[f"{prefix}_playing"] = False


def _toggle_play(prefix: str, last: int) -> None:
    if ss.get(f"{prefix}_playing"):
        ss[f"{prefix}_playing"] = False
    else:
        if ss.get(f"{prefix}_step", 0) >= last:
            ss[f"{prefix}_step"] = 0
        ss[f"{prefix}_playing"] = True


def _reveal(key: str) -> None:
    ss[key] = True


def stepper(prefix: str, n_steps: int):
    """Playback bar. Returns (current_step_index, predict_mode)."""
    last = n_steps - 1
    sk, pk = f"{prefix}_step", f"{prefix}_playing"
    ss.setdefault(sk, 0)
    ss.setdefault(pk, False)
    pending = ss.pop(f"{prefix}_pending", None)   
    if pending is not None:
        ss[sk] = pending
    ss[sk] = max(0, min(last, ss[sk]))
    cols = st.columns([0.55, 0.55, 1.15, 0.55, 0.55, 4.2, 1.5, 1.5])
    cols[0].button("⏮", key=f"{prefix}_first", on_click=_move, args=(prefix, "first", last), help="First step")
    cols[1].button("◀", key=f"{prefix}_prev", on_click=_move, args=(prefix, "prev", last), help="Previous step")
    predict = cols[7].checkbox("Predict mode", key=f"{prefix}_predict",
                               help="Hide each result until you press Reveal, so you can predict it first.")
    if predict:
        ss[pk] = False
    cols[2].button("⏸ Pause" if ss[pk] else "▶ Play", key=f"{prefix}_play", type="primary", disabled=predict,
                   on_click=_toggle_play, args=(prefix, last), help="Autoplay (disabled in Predict mode)")
    cols[3].button("▶|", key=f"{prefix}_next", on_click=_move, args=(prefix, "next", last), help="Next step")
    cols[4].button("⏭", key=f"{prefix}_last", on_click=_move, args=(prefix, "last", last), help="Last step")
    if last > 0:
        cols[5].select_slider("Step", options=list(range(n_steps)), key=sk, label_visibility="collapsed",
                              format_func=lambda v: f"Step {v + 1} of {n_steps}")
    else:
        cols[5].markdown("**Step 1 of 1**")
    cols[6].select_slider("Speed", options=list(SPEEDS), value="Medium", key=f"{prefix}_speed")
    return ss[sk], predict


def autoplay_tick(prefix: str, n_steps: int) -> None:
    if not ss.get(f"{prefix}_playing"):
        return
    step = ss[f"{prefix}_step"]
    if step >= n_steps - 1:
        ss[f"{prefix}_playing"] = False
        st.rerun()
    time.sleep(SPEEDS[ss.get(f"{prefix}_speed", "Medium")])
    ss[f"{prefix}_pending"] = step + 1
    st.rerun()


def shuttle_section(prefix: str, graph, route: List[str], outlined=()) -> None:
    """Shuttle glides along the final road-by-road route"""
    st.markdown("#### 🚌 Shuttle along the final route")
    if len(route) < 2:
        st.info("The route has a single location, so there is nothing to animate.")
        return
    speed = st.select_slider("Shuttle speed", options=["Slow", "Medium", "Fast"], value="Medium", key=f"{prefix}_ship_speed")
    frame_ms = {"Slow": 55, "Medium": 30, "Fast": 14}[speed]
    show_fig(vz.build_animated_route_figure(graph, route, outlined=list(outlined), frame_ms=frame_ms), f"{prefix}_anim")
    st.caption("Press ▶ Drive shuttle inside the chart. The bus follows the whole route in one continuous motion.")


#Overview Page
def page_overview() -> None:
    vz.hero("Smart Society Shuttle - Interactive Dynamic Programming and Routing",
            "A simulated shuttle connects society blocks and facilities to the Metro Station. "
            "Dijkstra finds shortest roads, Travelling Salesman with Dynamic Programming orders the stops.")

    st.write("")
    left, right = st.columns([3, 2])
    with left:
        view = st.radio("View", ["Graph view", "Map view"], horizontal=True, key="ov_view",
                        label_visibility="collapsed")
        if view == "Map view":
            st.markdown("#### Society Shuttle Plan")
            show_fig(vz.build_map_figure(), "ov_map")
            st.markdown('<span style="color:#000000; font-size:0.9rem;">A drawn plan of the society road network using the same layout as the graph. Switch to Graph view to see road costs.</span>', unsafe_allow_html=True)
        else:
            st.markdown("#### The society road network (conceptual layout)")
            show_fig(vz.build_graph_figure(BASE_GRAPH, height=460), "ov_graph")
    with right:
        vz.card("A residential society needs a shuttle that serves several places in one trip and ends at the destination like Metro Station. "
                "Roads are slower in peak hours and sometimes blocked. The system must <b>(1)</b> find the cheapest road "
                "between two places and <b>(2)</b> choose the cheapest <i>order</i> in which to visit several mandatory stops.",
                "🎯 The real-world routing problem")
        vz.card("<b>🧭 Module 1 · Dijkstra Routing</b> — single-source shortest path between two locations, shown one "
                "relaxation at a time.<br><br><b>🚌 Module 2 · Multi-Stop TSP</b> — backward DP <code>g(i, S)</code> "
                "over a cost matrix of shortest-path costs, in two modes: <i>TSP tour</i> (return to Main Gate) and "
                "<i>Shuttle-to-Metro</i> (finish at Metro Station).", "🧩 Two routing modules")
    c1, c2, c3 = st.columns(3)
    with c1:
        vz.card("Road graph (11 locations, 17 roads) · start · destination · required stops · traffic condition · blocked roads.",
                "📥 Inputs")
    with c2:
        vz.card("Shortest route and cost (Dijkstra) · optimal visiting order · road-by-road route · total cost · "
                "DP states · measured run time.", "📤 Outputs")
    with c3:
        vz.card("Each required stop visited once · roads are undirected · costs are non-negative · blocked roads are removed "
                "in both directions · small stop sets (TSP-DP is exponential).", "🔒 Constraints")
    boxes = ["Road graph", "Apply traffic + blocked roads", "Dijkstra: shortest cost between selected places",
             "Complete cost matrix c[i][j]", "Backward DP g(i, S) + stored choices", "Optimal visiting order",
             "Expand to road-by-road route"]
    flow = '<span class="arrow">➜</span>'.join(f'<div class="box">{b}</div>' for b in boxes)
    vz.card(f'<div class="flow">{flow}</div>', "🔄 From graph input to route output")
    vz.card("Dijkstra is used twice: directly in module 1, and as <b>preprocessing</b> for module 2 (repeated Dijkstra from each "
            "selected place). The TSP recurrence then runs on the complete matrix — so a stop that has no direct road "
            "(e.g. Main Gate → Hospital) still gets a finite cost through intermediate junctions.", "🔗 How the algorithms work together")


#Dijkstra Routing Page
def page_dijkstra() -> None:
    vz.hero("Dijkstra Routing - Shortest Road Between Two Locations",
            "Scanning-based Dijkstra. See each location get finalised and each road get relaxed.")
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1.4])
    start = c1.selectbox("Start location", LOCATIONS, index=0, key="dj_start")
    dest = c2.selectbox("Destination", LOCATIONS, index=7, key="dj_dest")
    traffic, blocked = condition_inputs("dj", c3)
    c4.caption("Pick any number of blocked roads in the box on the left, both directions are removed.")
    if start == dest:
        st.error("Start and destination must be different locations.")
        return
    graph = apply_conditions(BASE_GRAPH, traffic, blocked)
    t0 = time.perf_counter()
    res = dijkstra(graph, start, dest)
    run_ms = (time.perf_counter() - t0) * 1000
    steps = res.steps
    sig = (start, dest, traffic, tuple(blocked))
    if ss.get("dj_sig") != sig:
        ss["dj_sig"] = sig
        ss["dj_pending"] = 0
        ss["dj_playing"] = False
    step, predict = stepper("dj", len(steps))
    s = steps[step]
    rev_key = f"dj_rev_{step}"
    has_question = predict and s["kind"] == "select"
    hidden = has_question and not ss.get(rev_key, False)
    view = {**steps[step - 1], "current": None, "edge": None} if hidden else s

    roles: Dict[str, str] = {start: "start", dest: "target"}
    for n in view["visited"]:
        roles[n] = "visited"
    if view.get("current"):
        roles[view["current"]] = "current"
    edge = view.get("edge")
    if edge:
        roles[edge[1]] = "candidate"
    route = [res.path] if (s["kind"] == "path" and res.reachable) else []

    g1, g2 = st.columns([3, 2])
    with g1:
        show_fig(vz.build_graph_figure(graph, roles=roles, route_paths=route, relaxed_edge=edge, blocked=blocked,
        shuttle_at=start, outlined=[start, dest]), "dj_graph")
        st.markdown(vz.legend_html(["current", "candidate", "visited", "target"]), unsafe_allow_html=True)
    with g2:
        msg = "🔮 Predict: which unvisited location will be finalised next?" if hidden else s["message"]
        vz.card(f'<span class="badge">Step {step + 1} / {len(steps)}</span><br><br>{msg}', "Data flow for this step", accent=True)
        if hidden:
            options = sorted(s["frontier"], key=LOCATIONS.index)
            st.selectbox("Your prediction (smallest tentative distance)", options, key=f"dj_guess_{step}")
            st.button("Reveal result", key=f"dj_revbtn_{step}", type="primary", on_click=_reveal, args=(rev_key,))
        elif has_question:
            guess = ss.get(f"dj_guess_{step}")
            if guess == s["current"]:
                st.success(f"Your prediction ({guess}) was correct.")
            else:
                st.warning(f"You predicted {guess}; the algorithm finalised {s['current']}.")
        vz.card(vz.pseudocode_html(DIJKSTRA_PSEUDOCODE, None if hidden else s["line"]), "Pseudocode")

    t1, t2 = st.columns([3, 2])
    with t1:
        rows, row_cls = [], {}
        for r, n in enumerate(LOCATIONS):
            d = view["dist"][n]
            status = ("Current" if n == view.get("current") else "Visited" if n in view["visited"]
                      else "Frontier" if d < INF else "Not reached")
            if status == "Current":
                row_cls[r] = "hl"
            rows.append([tag(n), vz.fmt_cost(d, "∞"), view["prev"][n] or "—", status])
        vz.card(vz.html_table(["Location", f"Tentative distance ({COST_UNIT})", "Previous", "Status"], rows, row_cls=row_cls),
                "Distance table")
    with t2:
        if s["kind"] == "path" or step == len(steps) - 1:
            if res.reachable:
                body = (f"<b>Route:</b> {' → '.join(res.path)}<br><b>Total travel cost:</b> {vz.fmt_cost(res.cost)} {COST_UNIT}"
                        f"<br><b>Locations finalised:</b> {len(res.steps[-1]['visited'])}<br><b>Measured time:</b> {run_ms:.3f} ms")
            else:
                body = f"<b>No route.</b> {s['message']}"
        else:
            body = "Reach the last step to see the final route and cost."
        vz.card(body, "Final route and cost")
        with st.expander("Operation log up to this step"):
            for k, st_ in enumerate(steps[: step + 1]):
                st.markdown(f"`{k + 1}.` {st_['message']}")
    if res.reachable:
        shuttle_section("dj", graph, res.path, outlined=[start, dest])
    else:
        st.error(f"No road path from {start} to {dest} with the selected blocked roads. No route is shown.")
    autoplay_tick("dj", len(steps))


#Multi-Stop TSP Page
DEFAULT_TSP = dict(mode=MODE_METRO, start="Main Gate", stops=["Market", "Hospital"], destination="Metro Station",
                   traffic="Normal", blocked=[])

def run_tsp(inputs: dict) -> None:
    graph = apply_conditions(BASE_GRAPH, inputs["traffic"], inputs["blocked"])
    ss["tsp_graph"] = graph
    try:
        ss["tsp_solution"] = solve_route(graph, inputs["start"], inputs["stops"], inputs["destination"], inputs["mode"])
        ss["tsp_error"] = None
    except (RouteError, ValueError) as exc:
        ss["tsp_solution"] = None
        ss["tsp_error"] = str(exc)
    ss["tsp_inputs"] = inputs
    ss["tsp_pending"] = 0
    ss["tsp_playing"] = False


def recurrence_html(destination_mode: bool, terminal: str) -> str:
    if destination_mode:
        return ('<div class="recurrence"><b>Recurrence — Shuttle-to-Metro (terminal t = ' + terminal + ')</b><br>'
                'g(i, ∅) = c[i][t]<br>g(i, S) = min over j ∈ S of { c[i][j] + g(j, S − {j}) }<br>'
                'Answer = g(1, M),  M = required stops</div>')
    return ('<div class="recurrence"><b>Recurrence — TSP tour</b><br>g(i, ∅) = c[i][1]<br>'
            'g(i, S) = min over j ∈ S of { c[i][j] + g(j, S − {j}) }<br>Answer = g(1, V − {1})</div>')


def page_tsp() -> None:
    vz.hero("Travelling Salesman Problem — Smart Society Shuttle",
            "Backward dynamic programming g(i, S) on a cost matrix of shortest road costs. Unit IV.")
    if "tsp_inputs" not in ss:
        run_tsp(dict(DEFAULT_TSP))
    cur = ss["tsp_inputs"]
    sol = ss.get("tsp_solution")
    dest_mode = cur["mode"] == MODE_METRO
    h1, h2 = st.columns([3, 2])
    with h1:
        st.markdown("The shuttle starts at the **Main Gate** (city 1), visits every mandatory stop exactly once, and the "
                    "total travel cost is minimised. **g(i, S)** is the cheapest way to start at city *i*, visit all cities in "
                    "*S*, and then reach the terminal (Metro Station, or back to city 1 in the tour).")
        st.caption("Costs are travel minutes. Cities are numbered 1…n in the order: start, stops, destination.")
    with h2:
        st.markdown(recurrence_html(dest_mode, cur["destination"] or "Metro Station"), unsafe_allow_html=True)

    with st.expander("📥 Input data (change values, then press Run simulation)", expanded=True):
        with st.form("tsp_form"):
            f1, f2, f3 = st.columns(3)
            modes = [MODE_METRO, MODE_TEXTBOOK]
            mode = f1.radio("Route mode", modes, index=modes.index(cur["mode"]),
                            help="Shuttle-to-Metro is the practical mode, TSP tour returns to the start.")
            start = f1.selectbox("Start location (city 1)", LOCATIONS, index=LOCATIONS.index(cur["start"]))
            stops = f2.multiselect("Required stops", LOCATIONS, default=cur["stops"])
            dest = f2.selectbox("Destination (used in Shuttle-to-Metro mode)", LOCATIONS,
                                index=LOCATIONS.index(cur["destination"] or "Metro Station"))
            labels_default = [road_label(a, b) for a, b in cur["blocked"]]
            traffic = f3.selectbox("Traffic condition", list(TRAFFIC_MULTIPLIERS),
                                   index=list(TRAFFIC_MULTIPLIERS).index(cur["traffic"]))
            blocked_labels = f3.multiselect("Blocked roads (both directions)", list(ROAD_OPTIONS), default=labels_default)
            go_run = st.form_submit_button("Run simulation", type="primary")
        if go_run:
            run_tsp(dict(mode=mode, start=start, stops=list(stops), destination=dest, traffic=traffic,
                         blocked=[ROAD_OPTIONS[l] for l in blocked_labels]))
            st.rerun()

    graph = ss["tsp_graph"]
    if sol is None:
        st.error("Cannot compute a route: " + ss["tsp_error"])
        show_fig(vz.build_graph_figure(graph, blocked=cur["blocked"]), "tsp_err_graph")
        return

    tsp = sol.tsp
    steps = tsp.steps
    names = sol.nodes
    term_name = names[tsp.terminal]
    m = len(tsp.middle)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.markdown(vz.metric(f"Total route cost ({COST_UNIT})", vz.fmt_cost(sol.total_cost)), unsafe_allow_html=True)
    mc2.markdown(vz.metric("DP states computed", f"{tsp.states_computed}  (m·2^(m−1)+1 = {expected_states(m)})"), unsafe_allow_html=True)
    mc3.markdown(vz.metric("DP execution time", f"{tsp.elapsed_s * 1000:.3f} ms"), unsafe_allow_html=True)
    mc4.markdown(vz.metric("Cost-matrix preprocessing", f"{sol.preprocessing_s * 1000:.3f} ms"), unsafe_allow_html=True)
    mc5.markdown(vz.metric("Mode", "Shuttle-to-Metro" if dest_mode else "TSP tour"), unsafe_allow_html=True)
    st.write("")

    step, predict = stepper("tsp", len(steps))
    s = steps[step]
    kind = s["kind"]
    rev_key = f"tsp_rev_{step}"
    has_question = predict and kind in ("state", "final") and len(s["candidates"]) > 1
    hidden = has_question and not ss.get(rev_key, False)

    roles: Dict[str, str] = {}
    for p in steps[:step]:
        if p["kind"] in ("base", "state"):
            roles[names[p["i"]]] = "processed"
    roles[names[0]] = "start"
    if dest_mode:
        roles[term_name] = "target"
    cand_paths, sel_paths, route_paths = [], [], []
    if kind == "base":
        roles[names[s["i"]]] = "current"
        sel_paths = [sol.paths[(s["i"], tsp.terminal)]]
    elif kind in ("state", "final"):
        i = s["i"]
        roles[names[i]] = "current"
        for c in s["candidates"]:
            roles[names[c["j"]]] = "candidate"
            cand_paths.append(sol.paths[(i, c["j"])])
        if not hidden:
            roles[names[s["best_j"]]] = "selected"
            sel_paths = [sol.paths[(i, s["best_j"])]]
    else:
        route_paths = [sol.road_route]
    shuttle = names[s["i"]] if kind in ("base", "state", "final") else names[0]

    g1, g2 = st.columns([3, 2])
    with g1:
        show_fig(vz.build_graph_figure(graph, roles=roles, route_paths=route_paths, selected_paths=sel_paths,
                                       candidate_paths=cand_paths, blocked=cur["blocked"], shuttle_at=shuttle,
                                       outlined=names), "tsp_graph")
        st.markdown(vz.legend_html(["current", "candidate", "selected", "processed", "target"]), unsafe_allow_html=True)
    with g2:
        i_name = names[s["i"]]
        if kind == "base":
            body = (f"<b>Line 1 · {KIND_TITLES[kind]}.</b> With no other stop left, the shuttle at city {s['i'] + 1} "
                    f"({i_name}) goes straight to the terminal {term_name}.<br><br>"
                    f"<code>g({s['i'] + 1}, ∅) = c[{s['i'] + 1}][{tsp.terminal + 1}] = {vz.fmt_cost(s['value'])}</code>"
                    f"<br>Stored next stop: {term_name}.")
        elif kind in ("state", "final"):
            label = "g(1, " + set_str(list(s["S"])) + ")" if kind == "final" else f"g({s['i'] + 1}, {set_str(list(s['S']))})"
            remaining = ", ".join(names[x] for x in s["S"]) or "nothing"
            outcome = ("<br>🔮 <b>Predict</b> which next stop j gives the minimum, then press Reveal." if hidden else
                       f"<br><b>Minimum:</b> {vz.fmt_cost(s['value'])} via j = {s['best_j'] + 1} ({names[s['best_j']]}) → "
                       f"stored: g = {vz.fmt_cost(s['value'])}, next = {names[s['best_j']]}.")
            if kind == "final" and not s["candidates"]:
                outcome = f"<br>No stops in between: g = c[1][{tsp.terminal + 1}] = {vz.fmt_cost(s['value'])}."
            body = (f"<b>Line {s['line']} · {KIND_TITLES[kind]} <code>{label}</code>.</b> The shuttle is at city "
                    f"{s['i'] + 1} ({i_name}) and still has to visit {remaining}, then reach {term_name}. "
                    f"Try every j ∈ S as the next stop and keep the cheapest <code>c[i][j] + g(j, S − {{j}})</code>.{outcome}")
        elif kind == "return":
            body = (f"<b>Line 7 · Return.</b> The optimal cost is <code>g(1, {set_str(list(s['S']))}) = "
                    f"{vz.fmt_cost(s['value'])}</code> {COST_UNIT}.")
        else:
            body = ("<b>Line 8 · Reconstruct.</b> Follow the stored j of each state: "
                    + " → ".join(names[k] for k in s["order"]) + ".")
        vz.card(f'<span class="badge">Step {step + 1} / {len(steps)}</span><br><br>{body}', "Data flow for this step", accent=True)
        if kind in ("state", "final") and s["candidates"]:
            best_row = {} if hidden else {r: "best" for r, c in enumerate(s["candidates"]) if c["j"] == s["best_j"]}
            rows = [[f"{c['j'] + 1} · {names[c['j']]}", vz.fmt_cost(c["cij"]),
                     f"g({c['j'] + 1}, {set_str(list(c['rest']))}) = {vz.fmt_cost(c['g_rest'])}",
                     "?" if hidden else vz.fmt_cost(c["total"])] for c in s["candidates"]]
            vz.card(vz.html_table(["Candidate j", f"c[{s['i'] + 1}][j]", "g(j, S − {j})", "Total"], rows, row_cls=best_row),
                    "Candidate transitions")
        if kind == "reconstruct":
            rows = [[f"g({d['i'] + 1}, {set_str(list(d['S']))})", f"{vz.fmt_cost(d['value'])}", f"{d['j'] + 1} · {names[d['j']]}"]
                    for d in s["decisions"]]
            vz.card(vz.html_table(["State", "Stored value", "Stored next j"], rows), "Stored decisions followed")
        if hidden:
            options = [f"{c['j'] + 1} · {names[c['j']]}" for c in s["candidates"]]
            st.selectbox("Your prediction: which j is the minimum?", options, key=f"tsp_guess_{step}")
            st.button("Reveal result", key=f"tsp_revbtn_{step}", type="primary", on_click=_reveal, args=(rev_key,))
        elif has_question:
            guess = ss.get(f"tsp_guess_{step}", "")
            correct = f"{s['best_j'] + 1} · {names[s['best_j']]}"
            (st.success if guess == correct else st.warning)(
                f"Your prediction {'was correct' if guess == correct else 'was ' + str(guess)}: the minimum is j = {correct}.")

    m1, m2, m3 = st.columns([1.25, 1.25, 1.1])
    with m1:
        n = len(names)
        rows, cells = [], {}
        for a in range(n):
            row = [f"{a + 1} · {LOCATION_ICONS[names[a]]} {names[a]}"]
            for b in range(n):
                row.append("—" if a == b else vz.fmt_cost(tsp.matrix[a][b]))
                if a == b:
                    cells[(a, b + 1)] = "diag"
            rows.append(row)
        if kind in ("base", "state", "final"):
            cells[(s["i"], 0)] = "cur"
            if kind == "base":
                cells[(s["i"], tsp.terminal + 1)] = "sel"
            else:
                for c in s["candidates"]:
                    cells[(s["i"], c["j"] + 1)] = "cand"
                if not hidden and s["candidates"]:
                    cells[(s["i"], s["best_j"] + 1)] = "sel"
        heads = ["c[i][j]"] + [f"{b + 1}" for b in range(n)]
        vz.card(vz.html_table(heads, rows, cell_cls=cells, first_col_header=True) +
                "<div style='font-size:0.78rem;color:#64748B;margin-top:6px'>Shortest road cost between the selected places "
                "(— on the diagonal).</div>", "Cost matrix c[i][j]")
    with m2:
        upto = step if hidden else step + 1
        done = [(k, p) for k, p in enumerate(steps[:upto]) if p["kind"] in ("base", "state", "final")]
        shown = done[-40:]
        rows, row_cls = [], {}
        for r, (k, p) in enumerate(shown):
            lab = f"g({p['i'] + 1}, {set_str(list(p['S']))})"
            rows.append([str(k + 1), lab, vz.fmt_cost(p["value"]), names[p["best_j"]]])
            if k == step:
                row_cls[r] = "hl"
        body = vz.html_table(["#", "state g(i,S)", "value", "stored next j"], rows, row_cls=row_cls) if rows else "No values stored yet."
        note = f"<div style='font-size:0.78rem;color:#64748B;margin-top:6px'>{len(done)} values stored" + \
               (f" (showing the latest {len(shown)})" if len(done) > len(shown) else "") + "</div>"
        vz.card(body + note, "Stored g(i, S) values")
    with m3:
        vz.card(vz.pseudocode_html(tsp_pseudocode(dest_mode), None if hidden else s["line"]), "Pseudocode")

    # ---- results
    st.markdown("### Result")
    chips = " <span class='arrow' style='color:#7B2CBF;font-weight:800'>➜</span> ".join(f"<b>{tag(nm)}</b>" for nm in sol.order_names)
    vz.card(chips + f"<br><br><b>Total cost:</b> {vz.fmt_cost(sol.total_cost)} {COST_UNIT} &nbsp;|&nbsp; "
            f"<b>Check:</b> Σ leg costs = {vz.fmt_cost(sum(l['cost'] for l in sol.legs))} = g(1, …) = {vz.fmt_cost(tsp.cost)}",
            "Optimised shuttle order", accent=True)
    leg_rows = [[str(k + 1), f"{names[l['a']]} → {names[l['b']]}", " → ".join(l["path"]), vz.fmt_cost(l["cost"])]
                for k, l in enumerate(sol.legs)]
    leg_rows.append(["", "Total", " → ".join(sol.road_route), vz.fmt_cost(sol.total_cost)])
    vz.card(vz.html_table(["Leg", "Between selected stops", "Road-by-road route", f"Cost ({COST_UNIT})"], leg_rows,
                          row_cls={len(leg_rows) - 1: "hl"}), "Expanded road-by-road route")
    with st.expander("Full computation log"):
        for k, p in enumerate(steps[: step + 1]):
            if p["kind"] == "base":
                st.markdown(f"`{k + 1}.` Line 1 · g({p['i'] + 1}, ∅) = c[{p['i'] + 1}][{tsp.terminal + 1}] = **{vz.fmt_cost(p['value'])}**")
            elif p["kind"] in ("state", "final"):
                terms = "; ".join(f"j={c['j'] + 1}: {vz.fmt_cost(c['cij'])}+{vz.fmt_cost(c['g_rest'])}={vz.fmt_cost(c['total'])}"
                                  for c in p["candidates"]) or "direct"
                st.markdown(f"`{k + 1}.` Line {p['line']} · g({p['i'] + 1}, {set_str(list(p['S']))}) = min[{terms}] = "
                            f"**{vz.fmt_cost(p['value'])}** (next {p['best_j'] + 1})")
            elif p["kind"] == "return":
                st.markdown(f"`{k + 1}.` Line 7 · return **{vz.fmt_cost(p['value'])}**")
            else:
                st.markdown(f"`{k + 1}.` Line 8 · tour: {' → '.join(names[x] for x in p['order'])}")
    shuttle_section("tsp", graph, sol.road_route, outlined=names)
    autoplay_tick("tsp", len(steps))


#Test Cases Page
def page_tests() -> None:
    vz.hero("Test Cases", "Deterministic scenarios. Pressing the button runs the real functions and checks assertions.")
    if st.button("▶ Run all tests", type="primary", key="run_tests"):
        ss["test_rows"] = run_all_tests()
    rows = ss.get("test_rows")
    if rows is None:
        table = [[tid, sc, inp, exp, "Not run yet", "—"] for tid, sc, inp, exp, _ in TEST_CATALOG]
        cells = {}
    else:
        table = [[r["id"], r["scenario"], r["input"], r["expected"], r["actual"], r["status"]] for r in rows]
        cells = {(k, 5): ("pass" if r["status"] == "Pass" else "fail") for k, r in enumerate(rows)}
        passed = sum(r["status"] == "Pass" for r in rows)
        (st.success if passed == len(rows) else st.error)(f"{passed} of {len(rows)} tests passed.")
    vz.card(vz.html_table(["ID", "Scenario", "Input", "Expected behaviour", "Actual result", "Status"], table, cell_cls=cells),
            "Test-case table")


#Performance & Complexity Page
def page_performance() -> None:
    vz.hero("Performance and Complexity", "Theoretical bounds of the implemented algorithms, next to real measurements.")
    rows = [
        ["Dijkstra (scanning / array version, as implemented)", "O(V² + E) - commonly O(V²)", "O(V) auxiliary (dist, prev, visited), excluding the graph",
         "Each of V rounds scans V nodes for the minimum, all edges are relaxed once."],
        ["Shortest-path preprocessing (repeated Dijkstra)", "O(k · V²) for k selected places", "O(k²) for the matrix + paths",
         "Used instead of Floyd–Warshall (which would be O(V³)). Runs before TSP-DP."],
        ["TSP backward DP g(i, S)", "O(n² · 2ⁿ)", "O(n · 2ⁿ) for g and the stored choices, excluding the input matrix",
         "m·2^(m−1)+1 states (m = stops between start and terminal), each tries ≤ m candidates."],
        ["Step log kept for the visualisation", "—", "O(n² · 2ⁿ) extra", "Candidate lists are recorded only so each step can be shown, the algorithm itself does not need them."],
    ]
    vz.card(vz.html_table(["Algorithm", "Time complexity", "Space complexity", "Notes"], rows), "Theoretical complexity")
    vz.card("TSP-DP is exact but exponential. It is suitable here "
            "because a shuttle serves only a handful of mandatory stops"
            )

    st.markdown("### Measured: Dijkstra from Main Gate (Normal traffic)")
    graph = apply_conditions(BASE_GRAPH)
    out = []
    for dest in LOCATIONS[1:]:
        best = INF
        for _ in range(200):
            t0 = time.perf_counter()
            r = dijkstra(graph, "Main Gate", dest, record_steps=False)
            best = min(best, time.perf_counter() - t0)
        out.append([tag(dest), vz.fmt_cost(r.cost), f"{best * 1e6:.1f} µs"])
    vz.card(vz.html_table(["Destination", f"Cost ({COST_UNIT})", "Best of 200 runs"], out), "Real runs of dijkstra()")

    st.markdown("### Measured: TSP-DP versus number of stops")
    st.caption("Main Gate → Metro Station, 1…8 required stops taken in a fixed order. DP time = best of 3. "
               "Brute force (all orders) is run once as a correctness baseline.")
    if st.button("Run experiment", type="primary", key="run_exp"):
        with st.spinner("Running real measurements…"):
            ss["exp_rows"] = run_scaling_experiment()
    exp = ss.get("exp_rows")
    if exp:
        table = [[str(r["stops"]), str(r["nodes"]), str(r["states"]), str(r["expected"]), f"{r['dp_ms']:.3f}",
                  f"{r['pre_ms']:.3f}", str(r["orders"]), f"{r['brute_ms']:.3f}", "✔" if r["same_cost"] else "✘"] for r in exp]
        vz.card(vz.html_table(["Stops", "Nodes n", "States computed", "m·2^(m−1)+1", "DP ms", "Matrix ms",
                               "Orders m!", "Brute-force ms", "Same cost"], table), "Measured results")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[r["stops"] for r in exp], y=[r["dp_ms"] for r in exp], name="TSP-DP (ms)", mode="lines+markers",
                                 line=dict(color="#7B2CBF", width=3)))
        fig.add_trace(go.Scatter(x=[r["stops"] for r in exp], y=[r["brute_ms"] for r in exp], name="Brute force (ms)",
                                 mode="lines+markers", line=dict(color="#F97316", width=3)))
        fig.update_layout(height=360, yaxis_type="log", xaxis_title="Required stops", yaxis_title="Measured time (ms, log scale)",
                          margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#fff", plot_bgcolor="#fff")
        show_fig(fig, "exp_chart")
        st.caption("Timings depend on this computer and Python run; compare the trend, not the exact milliseconds. "
                   "For very few stops brute force can be as fast or faster; the DP advantage grows with the number of stops.")
    else:
        st.info("Press **Run experiment** to measure the implemented functions on this machine.")


#Agorithm Comparison Page
def page_comparison() -> None:
    vz.hero("Algorithm Comparison", "What each algorithm solves, whether it is optimal, and when to use it.")
    rows = [
        ["Dijkstra", "Cheapest road between two places (single source)", "Yes, for non-negative costs", "O(V²) array version",
         "Any time a shortest road is needed; here also as TSP preprocessing"],
        ["TSP-DP g(i, S)", "Cheapest order to visit all required stops once", "Yes (exact)", "O(n²·2ⁿ) time, O(n·2ⁿ) space",
         "Small stop sets (up to roughly 15–20 stops)"],
        ["Greedy nearest-neighbour (conceptual, not implemented)", "Quickly builds some visiting order by always going to the closest unvisited stop",
         "No — can be far from optimal", "About O(n²)", "Very large inputs where a rough answer is acceptable"],
        ["Brute-force TSP (used only as a test baseline)", "Tries every visiting order", "Yes (exact)", "O(n!) time",
         "Tiny inputs and checking other algorithms"],
    ]
    vz.card(vz.html_table(["Algorithm", "Problem it solves", "Optimal?", "Approximate complexity", "When appropriate"], rows),
            "Side-by-side")
    c1, c2 = st.columns(2)
    with c1:
        vz.card("Dijkstra answers <i>how to travel between two places</i>; TSP-DP answers <i>in which order to visit several places</i>. "
                "They are complementary: TSP-DP needs the pairwise road costs that Dijkstra provides, so running TSP on direct "
                "edges only gives wrong or infinite answers.", "Dijkstra versus TSP-DP")
    with c2:
        vz.card("Brute force examines m! orders; DP reuses sub-answers g(j, S − {j}) so each state is computed once, giving "
                "about m²·2ᵐ work. Both give the same cost — the Performance page measures this with the real functions.",
                "Brute force versus dynamic programming")


#Project Methodology Page
def page_about() -> None:
    vz.hero("Project Methodology", "Problem, assumptions, design choices and limits of this prototype.")
    a, b = st.columns(2)
    with a:
        vz.card("A shuttle inside a residential society must (1) travel the cheapest road between two places and (2) visit "
                "several mandatory stops in the cheapest order, starting at the Main Gate and finishing at the Metro Station "
                ".", "Problem statement")
        vz.card("<b>Input:</b> road graph, traffic condition, blocked roads, start, destination, required stops, route mode.<br>"
                "<b>Output:</b> shortest route and cost, optimal visiting order, road-by-road route, total cost, DP states and run time.",
                "Input and output")
        vz.card("Roads are undirected with non-negative simulated costs (estimated minutes). Traffic multiplies every road "
                "equally. Blocked roads vanish in both directions. A stop is visited once, passing through a junction or another "
                "stop's location while travelling between stops is allowed.", "Assumptions")
        vz.card("Dijkstra fits non-negative road costs. TSP-DP gives the exact optimum for the small number of mandatory stops. "
                "Greedy nearest-neighbour is not exact; brute force is too slow as stops grow.",
                "Why these algorithms")
    with b:
        vz.card("1) Apply traffic and blocked roads to a copy of the graph. 2) Run Dijkstra from each selected place to get the "
                "complete cost matrix c and the road paths. 3) Run the backward recurrence g(i, S) on c, storing the minimising "
                "next stop j for every state. 4) Follow the stored j's to rebuild the order. 5) Replace each leg by its stored road "
                "path to get the real route; its cost equals g(1, …).", "How graph, matrix, recurrence and route connect")
        vz.card("TSP tour mode uses g(i, ∅) = c[i][1] and returns to city 1. Shuttle-to-Metro mode uses g(i, ∅) = c[i][t] with "
                "t = destination, excludes t from the stops to visit, and keeps the same minimisation over the next remaining stop.",
                "The destination-mode adaptation")
        vz.card("Simulated data only. TSP-DP is "
                "exponential, so the stop count is limited by the interface to what is practical.", "Limitations")
        vz.card("Real society shuttles, school buses, campus tours, delivery rounds, hospital supply runs.", "Practical applications")
        vz.card("Live traffic input, passenger pick-up demand, multiple shuttles, time windows, a map view, saving scenarios.",
                "Possible future enhancements")

with st.sidebar:
    st.markdown("## 🚌 Smart Society Shuttle")
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.markdown("---")
{"🏠 Overview": page_overview, "🧭 Dijkstra Routing": page_dijkstra, "🚌 Multi-Stop TSP": page_tsp,
 "✅ Test Cases": page_tests, "⏱️ Performance & Complexity": page_performance,
 "⚖️ Algorithm Comparison": page_comparison, "📘 Project Methodology": page_about}[page]()