# Credit: C (earliest-arrival and path core); A (integration, earliest_path, UI wiring).
# Integrated from: teammate_deliverables/C/c_earliest_path.ipynb → algorithm_C.py
# Role: Earliest arrival time and path sequence on canonical adj {src: [(Unix, tgt, edge_id), ...]} sorted by Unix.

from bisect import bisect_left
from collections import deque
from math import inf
from typing import Any, Dict, Hashable, List, Optional, Tuple

Node = Hashable
eID = Any

tempAdjItem = Tuple[int, Node, eID]
tempAdj = Dict[Node, List[tempAdjItem]]

prevRecord = Dict[str, Any]

Adj = Dict[str, List[Tuple[int, str, str]]]


def first_edge_idx(out_edges: List[tempAdjItem], current_t: int) -> int:
    edge_times = [item[0] for item in out_edges]
    return bisect_left(edge_times, current_t)


def calculate_earlist_arrival(
    adj: tempAdj,
    source: Node,
    start_time: int,
    target: Optional[Node] = None,
) -> Tuple[Dict[Node, int], Dict[Node, Optional[prevRecord]]]:
    """Earliest arrival from source at start_time. ``target`` is accepted for notebook parity only."""
    _ = target
    arrival_t: Dict[Node, int] = {source: start_time}
    prev: Dict[Node, Optional[prevRecord]] = {source: None}

    queue: deque = deque([source])
    in_queue = {source}

    while queue:
        cur_node = queue.popleft()
        in_queue.discard(cur_node)

        cur_time = arrival_t[cur_node]

        out_edges = adj.get(cur_node, [])
        if not out_edges:
            continue

        start_idx = first_edge_idx(out_edges, cur_time)
        for edge_t, next_node, eid in out_edges[start_idx:]:
            if edge_t < arrival_t.get(next_node, inf):
                arrival_t[next_node] = edge_t
                prev[next_node] = {
                    "prev_node": cur_node,
                    "prev_edge": eid,
                    "depart_t": edge_t,
                    "arrival_t": edge_t,
                }

                if next_node not in in_queue:
                    queue.append(next_node)
                    in_queue.add(next_node)

    return arrival_t, prev


def extract_path_sequence(
    source: Node,
    target: Node,
    prev: Dict[Node, Optional[prevRecord]],
    arrival_times: Optional[Dict[Node, int]] = None,
) -> Dict[str, Any]:
    if source == target:
        return {
            "found": True,
            "path_node": [source],
            "path_edge": [],
            "hop_count": 0,
            "final_arrival_t": arrival_times.get(target) if arrival_times else None,
        }

    if target not in prev:
        return {
            "found": False,
            "path_node": [],
            "path_edge": [],
            "hop_count": 0,
            "final_arrival_t": None,
        }

    reversed_nodes = [target]
    reversed_edges = []
    pivot = target

    while pivot != source:
        record = prev.get(pivot)
        if record is None:
            return {
                "found": False,
                "path_node": [],
                "path_edge": [],
                "hop_count": 0,
                "final_arrival_t": None,
            }

        prev_node = record["prev_node"]
        reversed_edges.append(
            {
                "src": prev_node,
                "tgt": pivot,
                "edge_id": record["prev_edge"],
                "depart_t": record["depart_t"],
                "arrival_t": record["arrival_t"],
            }
        )
        reversed_nodes.append(prev_node)
        pivot = prev_node

    path_nodes = list(reversed(reversed_nodes))
    path_edges = list(reversed(reversed_edges))
    hop_count = len(path_nodes) - 1

    return {
        "found": True,
        "path_node": path_nodes,
        "path_edge": path_edges,
        "hop_count": hop_count,
        "final_arrival_t": arrival_times.get(target) if arrival_times else None,
    }


def earliest_path(
    adj: Adj,
    source: str,
    target: str,
    start_time: int = 0,
) -> Dict[str, Any]:
    """
    Earliest arrival path from ``source`` to ``target`` (B/E ``adj`` format).
    Returns ``arrival_times``, ``prev``, plus ``extract_path_sequence`` fields.
    """
    arrival_times, prev = calculate_earlist_arrival(
        adj, source, start_time, target=target
    )
    path_info = extract_path_sequence(
        source, target, prev, arrival_times=arrival_times
    )
    out: Dict[str, Any] = {
        "arrival_times": arrival_times,
        "prev": prev,
    }
    out.update(path_info)
    return out


__all__ = [
    "Adj",
    "calculate_earlist_arrival",
    "earliest_path",
    "extract_path_sequence",
    "first_edge_idx",
]
