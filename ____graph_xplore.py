#!/usr/bin/env python3
"""
network_paths.py
================
Explore a biomedical knowledge graph with symmetrical edges while
always printing predicates in their semantic direction.

Key points
----------
* Graph.add_relation() inserts the asserted edge          subj -[pred]-> obj
  **and** a complementary reverse edge                    obj  -[pred]-rev-> subj
  (we just keep a flag `is_rev` on the stored edge).
* Traversal helpers (bfs_layers, dfs_sample, …) propagate the flag.
* Pretty-printers show:
      A -[pred]-> B      when following the asserted direction
      A <-[pred]- B      when stepping against it.
"""

from __future__ import annotations
from collections import deque, Counter
from random     import choice
from typing     import Dict, List, Tuple, Iterable, Generator, Optional, Set

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Node      = str
Predicate = str
Edge      = Tuple[Node, Predicate, Node, bool]   # bool = is_reverse?
Path      = List[Node]

# ---------------------------------------------------------------------------
# 1.  GRAPH
# ---------------------------------------------------------------------------

class Graph:
    """Bidirectional multi-graph, preserving a flag for reversed edges."""

    def __init__(self) -> None:
        # node → list[(neighbour, predicate, is_reverse)]
        self._adj: Dict[Node, List[Tuple[Node, Predicate, bool]]] = {}

    # -- helpers -----------------------------------------------------------

    def _ensure(self, n: Node) -> None:
        self._adj.setdefault(n, [])

    # -- edge insertion ----------------------------------------------------

    def add_relation(
        self,
        subj: Node,
        pred: Predicate,
        obj: Node,
        bidirectional: bool = True,
    ) -> None:
        """
        Store subj -[pred]-> obj and, if *bidirectional*,
        obj <-[pred]- subj (marked as reverse).
        """
        self._ensure(subj); self._ensure(obj)
        self._adj[subj].append((obj, pred, False))   # forward
        if bidirectional:
            self._adj[obj].append((subj, pred, True))  # reverse

    # -- adjacency ---------------------------------------------------------

    def neighbors(self, n: Node) -> Iterable[Tuple[Node, Predicate, bool]]:
        return self._adj.get(n, ())

    # -- sugar -------------------------------------------------------------

    def nodes(self) -> Iterable[Node]:
        return self._adj.keys()

    def __len__(self) -> int:
        return len(self._adj)

    def __iter__(self):
        return iter(self._adj)


def build_graph(
    triples: Iterable[Tuple[Node, Predicate, Node]],
    bidirectional: bool = True,
) -> Graph:
    g = Graph()
    for s, p, o in triples:
        g.add_relation(s, p, o, bidirectional=bidirectional)
    return g

# ---------------------------------------------------------------------------
# 2.  TRAVERSAL
# ---------------------------------------------------------------------------

# -- full DFS / BFS (unchanged semantics, now carry is_rev) ---------------

def dfs(g: Graph, start: Node) -> Tuple[List[Node], List[Edge]]:
    visited: Set[Node] = {start}
    order:  List[Node] = [start]
    edges:  List[Edge] = []

    def _visit(u: Node) -> None:
        for v, pred, rev in g.neighbors(u):
            if v not in visited:
                visited.add(v)
                edges.append((u, pred, v, rev))
                order.append(v)
                _visit(v)

    _visit(start)
    return order, edges


def bfs(g: Graph, start: Node) -> Tuple[List[Node], List[Edge]]:
    visited: Set[Node] = {start}
    queue: deque[Node] = deque([start])
    order, edges = [], []

    while queue:
        u = queue.popleft()
        order.append(u)
        for v, pred, rev in g.neighbors(u):
            if v not in visited:
                visited.add(v)
                edges.append((u, pred, v, rev))
                queue.append(v)
    return order, edges


# -- neighbourhood BFS grouped by hop-layer -------------------------------

def bfs_layers(
    g: Graph,
    start: Node,
    max_hops: int = 2,
) -> Tuple[
        Dict[int, List[Tuple[Optional[Node], Predicate, Node, bool]]],
        List[Edge],
]:
    layers: Dict[int, List[Tuple[Optional[Node], Predicate, Node, bool]]] = {
        0: [(None, None, start, False)]
    }
    visited = {start}
    queue: deque[Tuple[Node, int]] = deque([(start, 0)])
    edges: List[Edge] = []

    while queue:
        u, depth = queue.popleft()
        if depth == max_hops:
            continue
        for v, pred, rev in g.neighbors(u):
            if v not in visited:
                visited.add(v)
                edges.append((u, pred, v, rev))
                layer = depth + 1
                layers.setdefault(layer, []).append((u, pred, v, rev))
                queue.append((v, layer))
    return layers, edges


# -- depth-limited DFS chain sampling -------------------------------------

def dfs_sample(
    g: Graph,
    start: Node,
    max_depth: int = 3,
    limit_nodes: Optional[int] = None,
) -> Tuple[List[Node], List[Edge]]:
    visited = {start}
    order_nodes, order_edges = [start], []
    stack: List[Tuple[Node, int, Iterable[Tuple[Node, Predicate, bool]]]] = [
        (start, 0, iter(g.neighbors(start)))
    ]

    while stack and (limit_nodes is None or len(order_nodes) < limit_nodes):
        u, depth, nbr_iter = stack[-1]
        try:
            v, pred, rev = next(nbr_iter)
            if v not in visited and depth < max_depth:
                visited.add(v)
                order_nodes.append(v)
                order_edges.append((u, pred, v, rev))
                stack.append((v, depth + 1, iter(g.neighbors(v))))
        except StopIteration:
            stack.pop()
    return order_nodes, order_edges


# ---------------------------------------------------------------------------
# 3.  PRETTY-PRINTERS
# ---------------------------------------------------------------------------

def _arrow(pred: Predicate, rev: bool) -> str:
    return f"-[{pred}]->" if not rev else f"<-[{pred}]-"

def format_layers(
    layers: Dict[int, List[Tuple[Optional[Node], Predicate, Node, bool]]]
) -> str:
    lines: List[str] = []
    for depth in sorted(layers):
        lines.append(f"Layer {depth}:")
        for parent, pred, node, rev in layers[depth]:
            if parent is None:                       # root
                lines.append(f"  {node}")
            else:
                lines.append(f"  {parent} {_arrow(pred, rev)} {node}")
    return "\n".join(lines)


def format_chain(
    start: Node,
    edges: List[Edge],
) -> str:
    if not edges:
        return start
    parts: List[str] = [start]
    current = start
    for u, pred, v, rev in edges:
        # edges list is already in traversal order
        parts.append(_arrow(pred, rev))
        parts.append(v)
    return " ".join(parts)

# ---------------------------------------------------------------------------
# 4.  OPTIONAL SHORTEST PATH (unchanged API, now returns correct edges)
# ---------------------------------------------------------------------------

def shortest_path_bfs(
    g: Graph,
    start: Node,
    goal: Node,
) -> Optional[Tuple[List[Node], List[Edge]]]:
    queue: deque[Tuple[Node, List[Edge]]] = deque([(start, [])])
    visited: Set[Node] = {start}

    while queue:
        v, path_edges = queue.popleft()
        if v == goal:
            nodes = [start] + [e[2] for e in path_edges]
            return nodes, path_edges
        for w, pred, rev in g.neighbors(v):
            if w not in visited:
                visited.add(w)
                queue.append((w, path_edges + [(v, pred, w, rev)]))
    return None


# ---------------------------------------------------------------------------
# 5.  DEMONSTRATION
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    triples = [
        # Cholesterol & consequences
        ("HMGCR",                   "catalyzes",            "Mevalonate_Synthesis"),
        ("Mevalonate_Synthesis",    "produces",             "Cholesterol"),
        ("Cholesterol",             "elevates",             "LDL_Particle"),
        ("Elevated_Cholesterol",    "is_risk_factor_for",   "Atherosclerosis"),
        ("Atherosclerosis",         "leads_to",             "Coronary_Artery_Disease"),
        ("Atherosclerosis",         "predisposes_to",       "Stroke"),
        # Statin branch
        ("Statin_Therapy",          "reduces_risk_of",      "Myocardial_Infarction"),
        ("Statin",                  "inhibits",             "HMGCR"),
        ("Statin",                  "lowers",               "LDL_Particle"),
        ("Coronary_Artery_Disease", "managed_by",           "Statin_Therapy"),
        # PCSK9 inhibitors
        ("PCSK9",                   "degrades",             "LDL_Receptor"),
        ("PCSK9_Inhibitor",         "inhibits",             "PCSK9"),
        ("LDL_Receptor",            "clears",               "LDL_Particle"),
        # Inflammatory cascade
        ("LDL_Particle",            "accumulates_in",       "Intima"),
        ("Intima",                  "activates",            "Inflammatory_Cells"),
        ("Inflammatory_Cells",      "release",              "Cytokines"),
        ("Cytokines",               "promote",              "Plaque_Destabilisation"),
        ("Plaque_Destabilisation",  "can_cause",            "Myocardial_Infarction"),
        # Lifestyle & genetics
        ("Omega3_Fatty_Acids",      "reduce",               "Triglycerides"),
        ("Triglycerides",           "contribute_to",        "Atherosclerotic_Plaque"),
        ("Exercise",                "improves",             "Endothelial_Function"),
        ("Endothelial_Function",    "protects_against",     "Atherosclerosis"),
        ("APOB_Mutation",           "causes",               "Familial_Hypercholesterolemia"),
        ("Familial_Hypercholesterolemia", "raises",         "LDL_Particle"),
    ]

    g = build_graph(triples, bidirectional=True)
    start = choice(list(g.nodes()))
    print(f"\n🏥  Start concept: {start}\n")

    # -------- radius-2 neighbourhood -------------------------------------
    layers, rad_edges = bfs_layers(g, start, max_hops=2)
    print(format_layers(layers), "\n")

    # Relation counts in that neighbourhood
    freq = Counter(pred for _, pred, _, _ in rad_edges)
    if freq:
        print("Relation frequencies within radius-2:")
        for rel, n in freq.most_common():
            print(f"  {rel:<25} {n}")
        print()

    # -------- DFS chain sample -------------------------------------------
    chain_nodes, chain_edges = dfs_sample(g, start, max_depth=4)
    print("One DFS chain (≤4 hops):")
    print("  " + format_chain(chain_nodes[0], chain_edges), "\n")

    # -------- Shortest path to MI ----------------------------------------
    goal = "Myocardial_Infarction"
    sp = shortest_path_bfs(g, start, goal)
    if sp:
        nodes, edges = sp
        print(f"Shortest path {start} ➜ {goal}:")
        print("  " + format_chain(nodes[0], edges))
    else:
        print(f"No route found from {start} to {goal}.")
