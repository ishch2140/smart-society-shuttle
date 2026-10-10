"""
graph_data.py - Static data for the Smart Society Shuttle prototype.
"""
from __future__ import annotations

import copy
from typing import Dict, FrozenSet, Iterable, List, Tuple

COST_UNIT = "min"  

LOCATIONS: List[str] = [
    "Main Gate", "Block A", "Block B", "Block C", "Junction 1",
    "Junction 2", "Market", "Hospital", "School", "Metro Station", "Temple",
]

BASE_GRAPH: Dict[str, Dict[str, float]] = {
    "Main Gate": {"Block A": 4, "Block C": 6, "Metro Station": 12},
    "Block A": {"Main Gate": 4, "Block B": 3, "Junction 1": 4},
    "Block B": {"Block A": 3, "Block C": 2, "Junction 2": 4},
    "Block C": {"Block B": 2, "Market": 5, "Main Gate": 6},
    "Junction 1": {"Block A": 4, "Junction 2": 6, "Hospital": 5},
    "Junction 2": {"Block B": 4, "Junction 1": 6, "Market": 3, "School": 4},
    "Market": {"Block C": 5, "Junction 2": 3, "Metro Station": 6},
    "Hospital": {"Junction 1": 5, "School": 3, "Temple": 5},
    "School": {"Hospital": 3, "Junction 2": 4, "Metro Station": 8, "Temple": 4},
    "Metro Station": {"Market": 6, "School": 8, "Main Gate": 12},
    "Temple": {"Hospital": 5, "School": 4},
}

TRAFFIC_MULTIPLIERS: Dict[str, float] = {
    "Normal": 1.0,
    "Morning Peak": 1.35,
    "Evening Peak": 1.50,
}

LOCATION_ICONS: Dict[str, str] = {
    "Main Gate": "🚪", "Block A": "🏢", "Block B": "🏢", "Block C": "🏢",
    "Junction 1": "🔀", "Junction 2": "🔀", "Market": "🛒",
    "Hospital": "🏥", "School": "🎓", "Metro Station": "🚇", "Temple": "🛕",
}
SHUTTLE_ICON = "🚌"

NODE_POSITIONS: Dict[str, Tuple[float, float]] = {
    "Main Gate": (0.0, 2.6),
    "Block A": (2.0, 4.6),
    "Block B": (4.0, 3.4),
    "Block C": (2.4, 1.4),
    "Junction 1": (5.2, 5.3),
    "Junction 2": (6.6, 3.4),
    "Market": (6.2, 1.6),
    "Hospital": (9.0, 5.3),
    "School": (9.0, 3.2),
    "Metro Station": (10.5, 1.0),
    "Temple": (11.0, 4.3),
}

CURVED_EDGES: Dict[FrozenSet[str], Tuple[float, float]] = {
    frozenset({"Main Gate", "Metro Station"}): (4.0, -3.2),
}


def road_key(a: str, b: str) -> FrozenSet[str]:
    """Order-independent identifier of an undirected road."""
    return frozenset((a, b))


def list_roads(graph: Dict[str, Dict[str, float]] = BASE_GRAPH) -> List[Tuple[str, str, float]]:
    """Unique undirected roads (a, b, weight), ordered by LOCATIONS index."""
    order = {name: k for k, name in enumerate(LOCATIONS)}
    seen, roads = set(), []
    for a in LOCATIONS:
        for b in sorted(graph.get(a, {}), key=lambda n: order[n]):
            key = road_key(a, b)
            if key in seen:
                continue
            seen.add(key)
            roads.append((a, b, graph[a][b]))
    return roads


def road_label(a: str, b: str) -> str:
    return f"{a} ↔ {b}"


def validate_graph(graph: Dict[str, Dict[str, float]]) -> List[str]:
    """Return a list of problems (empty list = graph is a valid undirected graph)."""
    problems = []
    for a, nbrs in graph.items():
        for b, w in nbrs.items():
            if b not in graph:
                problems.append(f"{a} links to unknown location {b}")
            elif graph[b].get(a) != w:
                problems.append(f"Road {a}-{b} is not symmetric")
            if w < 0:
                problems.append(f"Road {a}-{b} has negative weight")
    return problems


def apply_conditions(
    base: Dict[str, Dict[str, float]],
    traffic: str = "Normal",
    blocked_roads: Iterable[Tuple[str, str]] = (),
) -> Dict[str, Dict[str, float]]:
    """
    Return a NEW graph with the traffic multiplier applied and blocked roads removed
    (both directions).
    """
    if traffic not in TRAFFIC_MULTIPLIERS:
        raise ValueError(f"Unknown traffic condition: {traffic!r}")
    factor = TRAFFIC_MULTIPLIERS[traffic]
    blocked = set()
    for a, b in blocked_roads:
        if a not in base or b not in base[a]:
            raise ValueError(f"Cannot block {a} - {b}: no such road")
        blocked.add(road_key(a, b))
    adjusted: Dict[str, Dict[str, float]] = {name: {} for name in base}
    for a, nbrs in base.items():
        for b, w in nbrs.items():
            if road_key(a, b) in blocked:
                continue
            adjusted[a][b] = round(w * factor, 2)
    return copy.deepcopy(adjusted)