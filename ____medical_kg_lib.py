#!/usr/bin/env python3
"""
medical_kg_lib.py
=================
Small helper layer that

1. keeps the knowledge graph on disk (pickle)
2. lets you *ingest* one or many raw text snippets (strings)
3. lets you *explore* the stored graph and returns the data
   structures you’ll want to visualise in a GUI.

Dependencies:  __medical_text_to_json, __json_to_relation_triples,
               ____network_paths     (all already in your folder)
"""

from __future__ import annotations
import json, pickle
from pathlib import Path
from random  import choice
from collections import Counter
from typing import List, Tuple, Dict, Any

# --- GPT helpers ----------------------------------------------------------
from __medical_text_to_json     import medical_text_to_json
from __json_to_relation_triples import json_to_relation_triples

# --- Graph & traversal utilities -----------------------------------------
from ____network_paths import (
    Graph, build_graph,
    bfs_layers, dfs_sample,
    format_layers, format_chain,
)

# -------------------------------------------------------------------------
# Configuration constants
# -------------------------------------------------------------------------
KG_FILE       = Path("medical_kg.pkl")
BIDIRECTIONAL = True      # insert complementary reverse edge
DEFAULT_HOPS  = 2         # neighbourhood radius
DEFAULT_DEPTH = 4         # DFS chain depth limit


# -------------------------------------------------------------------------
# Graph persistence helpers
# -------------------------------------------------------------------------
def _load_graph() -> Graph:
    if KG_FILE.exists():
        with KG_FILE.open("rb") as fh:
            return pickle.load(fh)
    return Graph()

def _save_graph(g: Graph) -> None:
    with KG_FILE.open("wb") as fh:
        pickle.dump(g, fh)


# -------------------------------------------------------------------------
# Normalisation util
# -------------------------------------------------------------------------
_normalise = lambda s: s.replace(" ", "_")


# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------
def ingest_texts(texts: List[str]) -> int:
    """
    Parse *texts* (list of strings), extract triples via GPT,
    insert into the persistent graph.

    Returns
    -------
    n_triples : int   number of **forward** triples added
    """
    graph = _load_graph()
    added = 0

    for txt in texts:
        # 1. free text -> hierarchical JSON -> triple list
        struct   = medical_text_to_json(txt)
        triples  = json_to_relation_triples(json.dumps(struct, ensure_ascii=False))

        # 2. insert into graph
        for subj, pred, obj in triples:
            graph.add_relation(_normalise(subj), pred, _normalise(obj),
                               bidirectional=BIDIRECTIONAL)
        added += len(triples)

    _save_graph(graph)
    return added


def explore_graph(
    focus: str | None = None,
    max_hops: int = DEFAULT_HOPS,
    dfs_depth: int = DEFAULT_DEPTH,
) -> Dict[str, Any]:
    """
    Load the persisted graph and return a neighbourhood snapshot.

    Parameters
    ----------
    focus     : node name to centre on; if None, picks a random node
    max_hops  : BFS radius
    dfs_depth : depth limit for DFS chain

    Returns
    -------
    dict with keys:
        'focus'          : str
        'layers_str'     : pretty-printed multi-line string of BFS layers
        'layers'         : raw layer dict from bfs_layers()
        'relation_freqs' : Counter of predicates within the neighbourhood
        'dfs_chain_str'  : pretty string of one DFS chain
        'dfs_chain_nodes': list[str]
        'dfs_chain_edges': list[(u, pred, v, is_rev)]
    """
    g = _load_graph()
    if not g.nodes():
        raise RuntimeError("Knowledge graph is empty – ingest some text first.")

    if focus is None:
        focus = choice(list(g.nodes()))
    elif focus not in g.nodes():
        raise ValueError(f"Concept '{focus}' not found in graph.")

    # 1. neighbourhood
    layers, edges = bfs_layers(g, focus, max_hops=max_hops)
    layers_str    = format_layers(layers)
    freq          = Counter(pred for _, pred, _, _ in edges)

    # 2. DFS chain sample
    chain_nodes, chain_edges = dfs_sample(g, focus, max_depth=dfs_depth)
    chain_str = format_chain(chain_nodes[0], chain_edges)

    return {
        "focus"          : focus,
        "layers_str"     : layers_str,
        "layers"         : layers,
        "relation_freqs" : freq,
        "dfs_chain_str"  : chain_str,
        "dfs_chain_nodes": chain_nodes,
        "dfs_chain_edges": chain_edges,
    }


# -------------------------------------------------------------------------
# Tiny demo when run directly (optional)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    sample_text = "Der M. biceps brachii hat zwei Köpfe: Caput longum und Caput breve."
    print("Ingesting sample text …")
    n = ingest_texts([sample_text])
    print(f"Added {n} triples.\n")

    info = explore_graph()
    print(f"Focus concept: {info['focus']}\n")
    print(info["layers_str"])
    print("\nOne DFS chain:\n ", info["dfs_chain_str"])
