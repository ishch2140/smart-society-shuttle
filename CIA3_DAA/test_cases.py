"""
test_cases.py - Deterministic test catalogue. Every test runs real code and uses assertions.
"""
from __future__ import annotations

import copy
import math
from typing import Callable, Dict, List, Tuple

from algorithms import (INF, MODE_METRO, MODE_TEXTBOOK, RouteError, brute_force_tsp, build_cost_matrix,
                        dijkstra, route_cost_on_graph, solve_route, tsp_backward, validate_selection)
from graph_data import BASE_GRAPH, apply_conditions, road_key, validate_graph

CLASS_MATRIX = [[0, 10, 15, 20], [5, 0, 9, 10], [6, 13, 0, 12], [8, 8, 9, 0]]
METRO_ROADS = [("Main Gate", "Metro Station"), ("Market", "Metro Station"), ("School", "Metro Station")]


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, abs_tol=1e-6)


def graph(traffic="Normal", blocked=()):
    return apply_conditions(BASE_GRAPH, traffic, blocked)

def t_dijkstra_normal():
    r = dijkstra(graph(), "Main Gate", "Metro Station")
    assert r.reachable and close(r.cost, 12) and r.path == ["Main Gate", "Metro Station"]
    return f"cost {r.cost:g}, path {' → '.join(r.path)}"


def t_dijkstra_hospital():
    r = dijkstra(graph(), "Main Gate", "Hospital")
    assert close(r.cost, 13) and r.path == ["Main Gate", "Block A", "Junction 1", "Hospital"]
    assert "Hospital" not in BASE_GRAPH["Main Gate"] 
    return f"cost {r.cost:g}, path {' → '.join(r.path)}"


def t_dijkstra_morning():
    r = dijkstra(graph("Morning Peak"), "Main Gate", "Metro Station")
    assert close(r.cost, 16.2)
    return f"cost {r.cost:g} (12 × 1.35)"


def t_dijkstra_evening():
    r = dijkstra(graph("Evening Peak"), "Main Gate", "Metro Station")
    assert close(r.cost, 18.0)
    return f"cost {r.cost:g} (12 × 1.50)"


def t_dijkstra_blocked():
    g = graph("Normal", [("Main Gate", "Metro Station")])
    assert "Metro Station" not in g["Main Gate"] and "Main Gate" not in g["Metro Station"]
    r = dijkstra(g, "Main Gate", "Metro Station")
    assert close(r.cost, 17) and r.path == ["Main Gate", "Block C", "Market", "Metro Station"]
    return f"cost {r.cost:g}, path {' → '.join(r.path)}"


def t_tsp_two_stops():
    s = solve_route(graph(), "Main Gate", ["Hospital", "Market"], "Metro Station", MODE_METRO)
    assert s.order_names == ["Main Gate", "Hospital", "Market", "Metro Station"] and close(s.total_cost, 29)
    bf, _ = brute_force_tsp(s.matrix, len(s.nodes) - 1)
    assert close(bf, s.total_cost)
    return f"{' → '.join(s.order_names)}, cost {s.total_cost:g} (matches brute force)"


def t_tsp_four_stops():
    s = solve_route(graph(), "Main Gate", ["Block B", "Market", "Hospital", "School"], "Metro Station", MODE_METRO)
    bf, _ = brute_force_tsp(s.matrix, len(s.nodes) - 1)
    assert close(bf, s.total_cost) and math.isfinite(s.total_cost)
    return f"{' → '.join(s.order_names)}, cost {s.total_cost:g} (matches brute force)"


def t_disconnected():
    g = graph("Normal", METRO_ROADS)
    r = dijkstra(g, "Main Gate", "Metro Station")
    assert not r.reachable and r.cost == INF and r.path == []
    try:
        solve_route(g, "Main Gate", ["Hospital", "Market"], "Metro Station", MODE_METRO)
    except RouteError as exc:
        return f"RouteError: {str(exc)[:70]}…"
    raise AssertionError("expected RouteError for a disconnected network")


def t_duplicates():
    errs = validate_selection(BASE_GRAPH, "Main Gate", ["Market", "Market"], "Metro Station", MODE_METRO)
    assert any("Duplicate" in e for e in errs)
    errs2 = validate_selection(BASE_GRAPH, "Main Gate", ["Main Gate", "Hospital"], "Metro Station", MODE_METRO)
    assert any("start" in e.lower() for e in errs2)
    errs3 = validate_selection(BASE_GRAPH, "Main Gate", [], "Metro Station", MODE_METRO)
    assert errs3
    return "duplicate / start-as-stop / empty stops all rejected"


def t_start_dest():
    e1 = validate_selection(BASE_GRAPH, "Main Gate", ["Market"], "Main Gate", MODE_METRO)
    e2 = validate_selection(BASE_GRAPH, "Main Gate", ["Market"], "Market", MODE_METRO)
    e3 = validate_selection(BASE_GRAPH, "Main Gate", ["Market"], "Nowhere", MODE_METRO)
    assert e1 and e2 and e3
    assert not validate_selection(BASE_GRAPH, "Main Gate", ["Market"], "Metro Station", MODE_METRO)
    return "same start/destination, destination-as-stop, unknown place all rejected"


def t_textbook_returns():
    s = solve_route(graph(), "Main Gate", ["Hospital", "Market", "School"], None, MODE_TEXTBOOK)
    assert s.order_names[0] == "Main Gate" and s.order_names[-1] == "Main Gate"
    assert sorted(s.order_names[:-1]) == sorted(["Main Gate", "Hospital", "Market", "School"])
    bf, _ = brute_force_tsp(s.matrix, 0)
    assert close(bf, s.total_cost)
    return f"{' → '.join(s.order_names)}, cost {s.total_cost:g}"


def t_metro_ends():
    s = solve_route(graph(), "Main Gate", ["Hospital", "Block B"], "Metro Station", MODE_METRO)
    assert s.order_names[0] == "Main Gate" and s.order_names[-1] == "Metro Station"
    assert s.order_names.count("Metro Station") == 1
    return f"{' → '.join(s.order_names)}"


def t_matrix_preprocessing():
    nodes = ["Main Gate", "Hospital", "Market"]
    m, paths, bad = build_cost_matrix(graph(), nodes)
    assert not bad and close(m[0][1], 13) and close(m[1][0], 13) and close(m[1][2], 10)
    assert all(math.isfinite(m[i][j]) for i in range(3) for j in range(3))
    assert paths[(0, 1)] == ["Main Gate", "Block A", "Junction 1", "Hospital"]
    return "c[Main Gate][Hospital] = 13 via Block A, Junction 1 (no direct road, still finite)"


def t_route_consistency():
    g = graph("Morning Peak")
    s = solve_route(g, "Main Gate", ["Hospital", "Market", "School"], "Metro Station", MODE_METRO)
    for (a, b), leg in zip(zip(s.tsp.order, s.tsp.order[1:]), s.legs):
        assert leg["path"][0] == s.nodes[a] and leg["path"][-1] == s.nodes[b]
    assert close(route_cost_on_graph(g, s.road_route), s.total_cost)
    return f"road route cost {route_cost_on_graph(g, s.road_route):g} = DP cost {s.total_cost:g}"


def t_class_example():
    r = tsp_backward(CLASS_MATRIX, 0)
    assert close(r.cost, 35) and r.order == [0, 1, 3, 2, 0]
    # g(i, S) values from the recurrence, checked by hand
    assert close(r.g[(1, 0)], 5) and close(r.g[(2, 0)], 6) and close(r.g[(3, 0)], 8)
    assert close(r.g[(2, 1 << 3)], 20) and close(r.g[(3, 1 << 2)], 15)  
    assert r.choice[(0, 0b1110)] == 1 and r.choice[(1, 1 << 3 | 1 << 2)] == 3
    return "cost 35, tour 1 → 2 → 4 → 3 → 1; stored g and choices match the hand calculation"


def t_recurrence_all():
    r = tsp_backward(CLASS_MATRIX, 0)
    for st in r.steps:
        if st["kind"] == "state":
            expect = min(c["cij"] + r.g[(c["j"], st["S_mask"] & ~(1 << c["j"]))] for c in st["candidates"])
            assert close(r.g[(st["i"], st["S_mask"])], expect)
    seq, mask = [0], 0b1110
    cur = 0
    while mask:
        j = r.choice[(cur, mask)]
        seq.append(j); mask &= ~(1 << j); cur = j
    assert seq == r.order[:-1]
    return f"all {r.states_computed} stored g(i,S) values re-checked; tour follows stored choices"


def t_dest_mode_small():
    c = [[0, 4, 9, 7, 3], [4, 0, 2, 6, 8], [9, 2, 0, 5, 4], [7, 6, 5, 0, 2], [3, 8, 4, 2, 0]]
    for t in (4, 3):
        r = tsp_backward(c, t)
        bf, _ = brute_force_tsp(c, t)
        assert close(r.cost, bf) and r.order[0] == 0 and r.order[-1] == t
        assert sorted(r.order) == sorted(set(range(5)))
    return "destination-mode DP equals brute force for two different terminals"


def t_determinism():
    runs = [solve_route(graph(), "Main Gate", ["Block B", "Market", "Hospital"], "Metro Station", MODE_METRO)
            for _ in range(3)]
    assert all(r.order_names == runs[0].order_names and r.road_route == runs[0].road_route and
               r.total_cost == runs[0].total_cost for r in runs)
    return "3 identical runs → identical order, route and cost"


def t_invalid_matrix():
    bad = [[0, INF, 3], [1, 0, 2], [4, 5, 0]]
    try:
        tsp_backward(bad, 0)
    except ValueError as exc:
        return f"ValueError: {str(exc)[:60]}…"
    raise AssertionError("inf must be rejected")


def t_graph_not_mutated():
    before = copy.deepcopy(BASE_GRAPH)
    apply_conditions(BASE_GRAPH, "Evening Peak", [("Main Gate", "Block A")])
    assert BASE_GRAPH == before and not validate_graph(BASE_GRAPH)
    try:
        apply_conditions(BASE_GRAPH, "Normal", [("Main Gate", "Hospital")])
    except ValueError:
        return "base graph unchanged; blocking a non-existent road raises ValueError"
    raise AssertionError("expected ValueError")


def t_blocked_both_dirs():
    g = graph("Normal", [("Block A", "Block B")])
    assert "Block B" not in g["Block A"] and "Block A" not in g["Block B"]
    assert road_key("Block A", "Block B") not in {road_key(a, b) for a in g for b in g[a]}
    return "Block A ↔ Block B removed in both directions"


def t_temple():
    assert not validate_graph(BASE_GRAPH) and len(BASE_GRAPH) == 11
    s = solve_route(graph(), "Main Gate", ["Temple", "Hospital"], "Metro Station", MODE_METRO)
    bf, _ = brute_force_tsp(s.matrix, len(s.nodes) - 1)
    assert close(bf, s.total_cost) and "Temple" in s.order_names
    return f"{' → '.join(s.order_names)}, cost {s.total_cost:g} (matches brute force)"


TEST_CATALOG: List[Tuple[str, str, str, str, Callable[[], str]]] = [
    ("T01", "Dijkstra, normal traffic", "Main Gate → Metro Station, Normal", "Cost 12 via the direct road", t_dijkstra_normal),
    ("T02", "Dijkstra needing intermediate nodes", "Main Gate → Hospital, Normal", "Cost 13 via Block A, Junction 1", t_dijkstra_hospital),
    ("T03", "Morning peak traffic", "Main Gate → Metro Station, ×1.35", "Cost 16.2", t_dijkstra_morning),
    ("T04", "Evening peak traffic", "Main Gate → Metro Station, ×1.50", "Cost 18.0", t_dijkstra_evening),
    ("T05", "Blocked road forces detour", "Block Main Gate ↔ Metro Station", "Cost 17 via Block C, Market", t_dijkstra_blocked),
    ("T06", "Blocked road removes both directions", "Block Block A ↔ Block B", "Neither direction remains", t_blocked_both_dirs),
    ("T07", "TSP, two required stops (Shuttle-to-Metro)", "Main Gate; Hospital, Market; → Metro Station", "Optimal order, cost 29, equals brute force", t_tsp_two_stops),
    ("T08", "TSP, four required stops", "Main Gate; Block B, Market, Hospital, School; → Metro", "Finite optimal cost equal to brute force", t_tsp_four_stops),
    ("T09", "Disconnected network", "Block all 3 roads into Metro Station", "Unreachable Dijkstra; TSP raises a clear error, no ∞ answer", t_disconnected),
    ("T10", "Duplicate / invalid stops", "Market twice; start as stop; no stops", "Validation errors", t_duplicates),
    ("T11", "Start / destination validation", "Same start & destination; destination as stop; unknown", "Validation errors", t_start_dest),
    ("T12", "TSP tour returns to Main Gate", "Main Gate; Hospital, Market, School", "Tour starts and ends at Main Gate", t_textbook_returns),
    ("T13", "Shuttle-to-Metro finishes at Metro", "Main Gate; Hospital, Block B → Metro", "Last stop is Metro Station", t_metro_ends),
    ("T14", "Cost-matrix preprocessing (bug fix)", "Main Gate, Hospital, Market", "No ∞; c[1][2] = 13 via intermediate roads", t_matrix_preprocessing),
    ("T15", "Expanded route consistency", "Morning Peak, 3 stops", "Legs connect; road cost = DP cost", t_route_consistency),
    ("T16", "Recurrence on a 4-city matrix", "Class matrix c (4 cities)", "Cost 35, tour 1-2-4-3-1, g values match", t_class_example),
    ("T17", "g(i,S) values obey the recurrence", "Class matrix c (4 cities)", "Every state equals min over its candidates", t_recurrence_all),
    ("T18", "Destination-mode recurrence", "5-city matrix, terminals 5 and 4", "Equals brute force; ends at terminal", t_dest_mode_small),
    ("T19", "Deterministic repeated runs", "3 runs, same input", "Identical results", t_determinism),
    ("T20", "Infinite / invalid cost matrix", "c[1][2] = ∞", "ValueError, not a fake solution", t_invalid_matrix),
    ("T21", "Original graph not mutated", "Apply Evening Peak + a blocked road", "BASE_GRAPH unchanged; bad block rejected", t_graph_not_mutated),
]


def run_all_tests() -> List[Dict[str, str]]:
    rows = []
    for tid, scenario, inp, expected, fn in TEST_CATALOG:
        try:
            actual, status = fn(), "Pass"
        except AssertionError as exc:
            actual, status = f"Assertion failed {exc}".strip(), "Fail"
        except Exception as exc:  # unexpected error is also a failure
            actual, status = f"{type(exc).__name__}: {exc}", "Fail"
        rows.append(dict(id=tid, scenario=scenario, input=inp, expected=expected, actual=actual, status=status))
    return rows


if __name__ == "__main__":
    out = run_all_tests()
    for r in out:
        print(r["id"], r["status"], "-", r["scenario"], "|", r["actual"])
    print(f"{sum(r['status'] == 'Pass' for r in out)}/{len(out)} passed")