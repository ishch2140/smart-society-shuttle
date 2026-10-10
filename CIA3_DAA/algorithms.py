"""
algorithms.py - Dijkstra (Unit III) and Travelling Salesman via backward dynamic
programming g(i, S) (Unit IV), plus the glue that turns a road graph into a TSP cost matrix.
Units used: III (Dijkstra, scanning version) and IV (TSP-DP). 
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from itertools import combinations, permutations
from typing import Dict, List, Optional, Sequence, Tuple

from graph_data import LOCATIONS, BASE_GRAPH

INF = math.inf
MODE_TEXTBOOK = "TSP Tour (return to start)"
MODE_METRO = "Shuttle-to-Metro Mode (finish at destination)"
EPS = 1e-9


class RouteError(Exception):
    """Raised when a route cannot be computed (invalid input or disconnected network)."""

DIJKSTRA_PSEUDOCODE = [
    "for each location v: dist[v] := ∞ ; prev[v] := none",
    "dist[source] := 0",
    "while some location is unvisited:",
    "    u := unvisited location with smallest dist[u]   (linear scan)",
    "    if dist[u] = ∞: stop            (rest is unreachable)",
    "    mark u as visited",
    "    if u = destination: stop",
    "    for each unvisited neighbour v of u with road cost w(u,v):",
    "        if dist[u] + w(u,v) < dist[v]:",
    "            dist[v] := dist[u] + w(u,v) ; prev[v] := u",
    "rebuild the path by following prev[] back from the destination",
]


@dataclass
class DijkstraResult:
    source: str
    target: Optional[str]
    dist: Dict[str, float]
    prev: Dict[str, Optional[str]]
    path: List[str]
    cost: float
    reachable: bool
    steps: List[dict] = field(default_factory=list)


def dijkstra(graph: Dict[str, Dict[str, float]], source: str, target: Optional[str] = None,
             record_steps: bool = True) -> DijkstraResult:
    if source not in graph:
        raise RouteError(f"Unknown start location: {source}")
    if target is not None and target not in graph:
        raise RouteError(f"Unknown destination: {target}")
    nodes = list(graph)       
    index = {n: k for k, n in enumerate(nodes)}
    dist = {n: INF for n in nodes}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes}
    visited: List[str] = []
    visited_set = set()
    steps: List[dict] = []

    def snap(kind: str, line: int, message: str, **extra) -> None:
        if record_steps:
            steps.append(dict(kind=kind, line=line, message=message, dist=dict(dist),
                              prev=dict(prev), visited=list(visited), **extra))

    snap("init", 1, "All distances start at ∞ and every location is unvisited.", current=None, edge=None)
    dist[source] = 0.0
    snap("init", 2, f"Distance of the start '{source}' is set to 0.", current=None, edge=None)

    while True:
        u, best = None, INF
        for n in nodes:
            if n not in visited_set and dist[n] < best:
                u, best = n, dist[n]
        frontier = {n: dist[n] for n in nodes if n not in visited_set and dist[n] < INF}
        if u is None:
            snap("stop", 5, "No unvisited location has a finite distance, so the rest are unreachable.",
                 current=None, edge=None)
            break
        visited.append(u)
        visited_set.add(u)
        snap("select", 4, f"'{u}' has the smallest tentative distance ({best:g}), so it is finalised.",
             current=u, edge=None, frontier=frontier)
        if target is not None and u == target:
            snap("done", 7, f"Destination '{target}' is finalised with cost {best:g}; stop.", current=u, edge=None)
            break
        for v in sorted(graph[u], key=lambda n: index[n]):
            if v in visited_set:
                continue
            w = graph[u][v]
            candidate = round(dist[u] + w, 2)
            old = dist[v]
            improved = candidate < old - EPS
            if improved:
                dist[v] = candidate
                prev[v] = u
            snap("relax", 10 if improved else 9,
                 (f"Relax {u} → {v}: {dist[u]:g} + {w:g} = {candidate:g} "
                  f"{'<' if improved else '≥'} {'∞' if old == INF else format(old, 'g')} "
                  f"→ {'updated' if improved else 'kept'}."),
                 current=u, edge=(u, v), old=old, cand=candidate, improved=improved, weight=w)

    path: List[str] = []
    cost = INF
    reachable = False
    if target is not None and dist[target] < INF:
        reachable = True
        cost = dist[target]
        node: Optional[str] = target
        while node is not None:
            path.append(node)
            node = prev[node]
        path.reverse()
    if target is not None:
        msg = (f"Shortest path: {' → '.join(path)} (cost {cost:g})." if reachable
               else f"No road path exists from '{source}' to '{target}'.")
        snap("path", 11, msg, current=None, edge=None, path=list(path))
    return DijkstraResult(source, target, dist, prev, path, cost, reachable, steps)

def build_cost_matrix(graph: Dict[str, Dict[str, float]], nodes: Sequence[str]):
    """
    Returns (matrix, paths, unreachable)
      matrix[i][j]  shortest road cost between nodes[i] and nodes[j] (INF if unreachable)
      paths[(i,j)]  list of road locations from nodes[i] to nodes[j]
      unreachable   list of (i, j) pairs (i<j) with no road path
    """
    n = len(nodes)
    matrix = [[0.0] * n for _ in range(n)]
    paths: Dict[Tuple[int, int], List[str]] = {}
    unreachable: List[Tuple[int, int]] = []
    for i, a in enumerate(nodes):
        res = dijkstra(graph, a, record_steps=False)
        for j, b in enumerate(nodes):
            if i == j:
                paths[(i, j)] = [a]
                continue
            if res.dist[b] < INF:
                matrix[i][j] = round(res.dist[b], 2)
                path, node = [], b
                while node is not None:
                    path.append(node)
                    node = res.prev[node]
                paths[(i, j)] = path[::-1]
            else:
                matrix[i][j] = INF
                if i < j:
                    unreachable.append((i, j))
    return matrix, paths, unreachable

def tsp_pseudocode(destination_mode: bool) -> List[str]:
    t = "t" if destination_mode else "1"
    mid = "M = {2,…,n} − {t}" if destination_mode else "V − {1} = {2,…,n}"
    return [
        f"1.  for each i ∈ {mid}:  g(i, ∅) := c[i][{t}]",
        f"2.  for s := 1 to |{'M' if destination_mode else 'V−{1}'}| − 1 do",
        f"3.      for each S ⊆ {'M' if destination_mode else '{2,…,n}'} with |S| = s do",
        f"4.          for each i ∉ S, i ≠ 1{', i ≠ t' if destination_mode else ''} do",
        "5.              g(i, S) := min { c[i][j] + g(j, S − {j}) : j ∈ S }",
        f"6.  g(1, {'M' if destination_mode else 'V − {1}'}) := min { '{' } c[1][j] + g(j, {'M' if destination_mode else 'V − {1}'} − {{j}}) : j ∈ {'M' if destination_mode else 'V − {1}'} { '}' }",
        f"7.  return g(1, {'M' if destination_mode else 'V − {1}'})",
        "8.  follow the stored minimising j's to reconstruct the optimal tour",
    ]


@dataclass
class TSPResult:
    n: int
    terminal: int
    middle: List[int]
    matrix: List[List[float]]
    g: Dict[Tuple[int, int], float]
    choice: Dict[Tuple[int, int], int]
    steps: List[dict]
    order: List[int]
    cost: float
    states_computed: int
    elapsed_s: float


def mask_of(items) -> int:
    m = 0
    for x in items:
        m |= 1 << x
    return m


def members_of(mask: int, n: int) -> List[int]:
    return [k for k in range(n) if mask >> k & 1]


def _validate_matrix(c: Sequence[Sequence[float]]) -> int:
    n = len(c)
    if n < 2:
        raise ValueError("TSP needs at least 2 cities")
    for i, row in enumerate(c):
        if len(row) != n:
            raise ValueError("Cost matrix must be square")
        for j, v in enumerate(row):
            if i == j:
                continue
            if not isinstance(v, (int, float)) or math.isnan(v) or math.isinf(v) or v < 0:
                raise ValueError(f"c[{i + 1}][{j + 1}] is not a finite non-negative cost "
                                 "(unreachable transitions must be handled before running TSP)")
    return n


def tsp_backward(c: Sequence[Sequence[float]], terminal: int = 0) -> TSPResult:
    """
    Backward DP for TSP.  c is a complete finite matrix; city index 0 is city 1.
    terminal = 0  -> textbook TSP (tour returns to city 1)
    terminal = t  -> shuttle-to-destination: visit all other cities once, finish at t.
    Tie-break: the smallest j wins (strict '<'), so repeated runs give identical tours.
    """
    n = _validate_matrix(c)
    if not 0 <= terminal < n:
        raise ValueError("terminal city out of range")
    start = 0
    middle = [k for k in range(n) if k != start and k != terminal]
    m = len(middle)
    full = mask_of(middle)
    g: Dict[Tuple[int, int], float] = {}
    choice: Dict[Tuple[int, int], int] = {}
    steps: List[dict] = []
    t0 = time.perf_counter()
    for i in middle:
        g[(i, 0)] = c[i][terminal]
        choice[(i, 0)] = terminal
        steps.append(dict(kind="base", line=1, i=i, S=(), S_mask=0, value=g[(i, 0)], best_j=terminal, candidates=[]))
    for s in range(1, m):
        for subset in combinations(middle, s):
            S = mask_of(subset)
            for i in middle:
                if S >> i & 1:
                    continue
                cands = []
                best_j, best_total = -1, INF
                for j in subset:
                    rest = S & ~(1 << j)
                    total = c[i][j] + g[(j, rest)]
                    cands.append(dict(j=j, cij=c[i][j], g_rest=g[(j, rest)], rest=tuple(members_of(rest, n)), total=total))
                    if total < best_total - EPS:
                        best_j, best_total = j, total
                g[(i, S)] = best_total
                choice[(i, S)] = best_j
                steps.append(dict(kind="state", line=5, i=i, S=subset, S_mask=S, value=best_total,
                                  best_j=best_j, candidates=cands))

    if m >= 1:
        cands = []
        best_j, best_total = -1, INF
        for j in middle:
            rest = full & ~(1 << j)
            total = c[start][j] + g[(j, rest)]
            cands.append(dict(j=j, cij=c[start][j], g_rest=g[(j, rest)], rest=tuple(members_of(rest, n)), total=total))
            if total < best_total - EPS:
                best_j, best_total = j, total
    else: 
        best_j, best_total, cands = terminal, c[start][terminal], []
    g[(start, full)] = best_total
    choice[(start, full)] = best_j
    steps.append(dict(kind="final", line=6, i=start, S=tuple(middle), S_mask=full, value=best_total,
                      best_j=best_j, candidates=cands))
    elapsed = time.perf_counter() - t0
    steps.append(dict(kind="return", line=7, i=start, S=tuple(middle), S_mask=full, value=best_total,
                      best_j=best_j, candidates=[]))

    order, decisions = [start], []
    cur, mask = start, full
    while True:
        j = choice[(cur, mask)]
        decisions.append(dict(i=cur, S=tuple(members_of(mask, n)), j=j, value=g[(cur, mask)]))
        order.append(j)
        if mask == 0:
            break
        mask &= ~(1 << j)
        cur = j
    steps.append(dict(kind="reconstruct", line=8, i=start, S=tuple(middle), S_mask=full, value=best_total,
                      best_j=best_j, candidates=[], decisions=decisions, order=list(order)))
    return TSPResult(n, terminal, middle, [list(r) for r in c], g, choice, steps, order,
                     best_total, len(g), elapsed)


def brute_force_tsp(c: Sequence[Sequence[float]], terminal: int = 0) -> Tuple[float, List[int]]:
    """Exhaustive check (all visiting orders). Used only to verify / compare against the DP."""
    n = _validate_matrix(c)
    middle = [k for k in range(n) if k != 0 and k != terminal]
    best, best_order = INF, [0, terminal]
    for perm in permutations(middle):
        seq = [0, *perm, terminal]
        total = sum(c[a][b] for a, b in zip(seq, seq[1:]))
        if total < best - EPS:
            best, best_order = total, seq
    return best, best_order


@dataclass
class RouteSolution:
    mode: str
    start: str
    stops: List[str]
    destination: Optional[str]
    nodes: List[str]
    matrix: List[List[float]]
    paths: Dict[Tuple[int, int], List[str]]
    tsp: TSPResult
    order_names: List[str]
    legs: List[dict]
    road_route: List[str]
    total_cost: float
    preprocessing_s: float


def validate_selection(graph, start, stops, destination, mode) -> List[str]:
    errors: List[str] = []
    stops = list(stops or [])
    if not start:
        errors.append("Choose a start location.")
    elif start not in graph:
        errors.append(f"Unknown start location: {start}.")
    for s in stops:
        if s not in graph:
            errors.append(f"Unknown stop: {s}.")
    if len(set(stops)) != len(stops):
        errors.append("Duplicate required stops are not allowed, each stop is visited once.")
    if start in stops:
        errors.append("The start location cannot also be a required stop.")
    if not stops:
        errors.append("Select at least one required stop.")
    if mode == MODE_METRO:
        if not destination:
            errors.append("Choose a destination.")
        elif destination not in graph:
            errors.append(f"Unknown destination: {destination}.")
        else:
            if destination == start:
                errors.append("Start and destination must be different in Shuttle-to-Metro mode.")
            if destination in stops:
                errors.append("The destination cannot also be a required stop.")
    elif mode != MODE_TEXTBOOK:
        errors.append(f"Unknown route mode: {mode}.")
    return errors


def solve_route(graph, start: str, stops: Sequence[str], destination: Optional[str], mode: str) -> RouteSolution:
    errors = validate_selection(graph, start, stops, destination, mode)
    if errors:
        raise RouteError(" ".join(errors))
    stops = list(stops)
    nodes = [start, *stops] + ([destination] if mode == MODE_METRO else [])
    t0 = time.perf_counter()
    matrix, paths, unreachable = build_cost_matrix(graph, nodes)
    pre = time.perf_counter() - t0
    if unreachable:
        pairs = ", ".join(f"{nodes[i]} ↔ {nodes[j]}" for i, j in unreachable[:4])
        more = "" if len(unreachable) <= 4 else f" (+{len(unreachable) - 4} more)"
        raise RouteError("No road path connects: " + pairs + more +
                         ". The network is disconnected for these locations (check blocked roads).")
    terminal = len(nodes) - 1 if mode == MODE_METRO else 0
    tsp = tsp_backward(matrix, terminal)
    legs, route = [], [nodes[tsp.order[0]]]
    for a, b in zip(tsp.order, tsp.order[1:]):
        seg = paths[(a, b)]
        legs.append(dict(a=a, b=b, path=seg, cost=matrix[a][b]))
        route.extend(seg[1:])
    leg_sum = round(sum(l["cost"] for l in legs), 2)
    if not math.isclose(leg_sum, tsp.cost, abs_tol=1e-6) or not math.isfinite(tsp.cost):
        raise RuntimeError("Internal consistency check failed: leg costs do not add up to the DP cost")
    return RouteSolution(mode, start, stops, destination if mode == MODE_METRO else None, nodes, matrix,
                         paths, tsp, [nodes[k] for k in tsp.order], legs, route, round(tsp.cost, 2), pre)


def route_cost_on_graph(graph, route: Sequence[str]) -> float:
    """Sum road weights along a road-by-road route, raises RouteError on a missing road."""
    total = 0.0
    for a, b in zip(route, route[1:]):
        if b not in graph.get(a, {}):
            raise RouteError(f"No road between {a} and {b}")
        total += graph[a][b]
    return round(total, 2)


def expected_states(num_middle: int) -> int:
    """Number of g(i,S) values: m * 2^(m-1) for the table plus the final g(1, M)."""
    return num_middle * 2 ** (num_middle - 1) + 1 if num_middle >= 1 else 1


EXPERIMENT_POOL = ["Block A", "Block B", "Block C", "Market", "Hospital", "School", "Junction 1", "Junction 2"]


def run_scaling_experiment(graph=BASE_GRAPH, max_stops: int = 8, repeats: int = 3) -> List[dict]:
    """Measured runtimes of the real functions (Shuttle-to-Metro mode, Main Gate -> Metro Station)."""
    rows = []
    for k in range(1, max_stops + 1):
        stops = EXPERIMENT_POOL[:k]
        nodes = ["Main Gate", *stops, "Metro Station"]
        t0 = time.perf_counter()
        matrix, _, bad = build_cost_matrix(graph, nodes)
        pre_ms = (time.perf_counter() - t0) * 1000
        if bad:
            raise RouteError("Experiment graph is disconnected")
        dp_best, res = INF, None
        for _ in range(repeats):
            t0 = time.perf_counter()
            res = tsp_backward(matrix, len(nodes) - 1)
            dp_best = min(dp_best, (time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        bf_cost, _ = brute_force_tsp(matrix, len(nodes) - 1)
        bf_ms = (time.perf_counter() - t0) * 1000
        rows.append(dict(stops=k, nodes=len(nodes), states=res.states_computed, expected=expected_states(k),
                         pre_ms=pre_ms, dp_ms=dp_best, brute_ms=bf_ms, orders=math.factorial(k),
                         same_cost=math.isclose(bf_cost, res.cost, abs_tol=1e-6), cost=res.cost))
    return rows
