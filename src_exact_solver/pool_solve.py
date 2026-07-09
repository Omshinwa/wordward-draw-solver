"""Matheuristic: exact Steiner solve over a candidate grey pool.

The full 2283-node instance is too dense to solve exactly, but the optimum only
uses a few dozen greys. We gather a pool of "useful" greys from many randomized
heuristic solutions, then solve the Steiner problem *exactly* on the small
induced subgraph (terminals + pool). The result is optimal within the pool and a
valid, playable solution on the full graph -- an upper bound on the true optimum.
"""
import sys
import time
import random
import pickle

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # sibling exact-solver modules
sys.path.insert(0, os.path.join(_HERE, os.pardir, "src"))  # word_set, utils
from exact_solver import build_graph  # noqa: E402
from heuristic import grow_tree, prune, eliminate, greys_of, kmb  # noqa: E402
from scip_solver import solve_core  # noqa: E402


def collect_pool(n, is_term, adj, terms, seconds=90, keep_delta=3, seed=1,
                 verbose=True):
    rng = random.Random(seed)
    pool = set()
    best = 10 ** 9
    best_tree = None
    solutions = []

    def register(tree):
        nonlocal best, best_tree
        prune(n, is_term, adj, tree)
        eliminate(n, is_term, adj, terms, tree)
        gc = len(greys_of(n, is_term, tree))
        solutions.append((gc, bytearray(tree)))
        if gc < best:
            best, best_tree = gc, bytearray(tree)
        return gc

    register(kmb(n, is_term, adj, terms))
    for s in terms:
        register(grow_tree(n, is_term, adj, terms, s))

    t0 = time.time()
    it = 0
    while time.time() - t0 < seconds:
        it += 1
        w = [0.0 if is_term[v] else 1.0 + rng.uniform(0, 0.9) for v in range(n)]
        register(grow_tree(n, is_term, adj, terms, rng.choice(terms), weight=w))

    for gc, tree in solutions:
        if gc <= best + keep_delta:
            for v in range(n):
                if tree[v] and not is_term[v]:
                    pool.add(v)
    if verbose:
        print(f"collected {len(pool)} candidate greys from {len(solutions)} "
              f"solutions (best {best} greys); {it} random iters")
    return pool, best, best_tree


def induced(n, is_term, adj, allowed):
    "Relabel the subgraph induced on `allowed` (a set of node indices)."
    nodes = sorted(allowed)
    old2new = {v: i for i, v in enumerate(nodes)}
    n2 = len(nodes)
    is_term2 = [is_term[v] for v in nodes]
    adj2 = [[] for _ in range(n2)]
    for i, v in enumerate(nodes):
        for w in adj[v]:
            if w in old2new:
                adj2[i].append(old2new[w])
    edges2 = [(i, j) for i in range(n2) for j in adj2[i] if i < j]
    return nodes, old2new, n2, is_term2, adj2, edges2


def solve(name="graph_optimal_2283", pool_seconds=90, mip_seconds=600,
          keep_delta=1, root_sep_full=False):
    ids, idx, n, is_term, adj, edges, g = build_graph(name)
    terms = [i for i in range(n) if is_term[i]]

    pool, best, best_tree = collect_pool(n, is_term, adj, terms,
                                         seconds=pool_seconds, keep_delta=keep_delta)
    allowed = set(terms) | pool
    nodes, old2new, n2, is_term2, adj2, edges2 = induced(n, is_term, adj, allowed)
    print(f"induced subgraph: {n2} nodes ({sum(is_term2)} terminals), {len(edges2)} edges")

    warm = bytearray(n2)
    for v in range(n):
        if best_tree[v]:
            warm[old2new[v]] = 1

    t0 = time.time()
    chosen, greys, lb, status = solve_core(
        n2, is_term2, adj2, edges2, warm_tree=warm,
        time_limit=mip_seconds, root_sep_full=root_sep_full, verbose=True)
    print(f"\npool solve: status={status}  time={time.time()-t0:.1f}s")
    print(f"  within-pool dual bound >= {lb:.3f} greys")
    print(f"  best in pool: {greys} greys  ->  operations = {106 + greys}")
    print(f"  (heuristic best was {best} greys = {106 + best} operations)")

    final_greys = greys if greys is not None and greys <= best else best
    final_nodes = ([nodes[i] for i in chosen] if (greys is not None and greys <= best)
                   else [v for v in range(n) if best_tree[v]])
    chosen_ids = [ids[v] for v in final_nodes]
    print(f"\n=> FINAL: {final_greys} greys -> operations = {106 + final_greys} "
          f"(record was 173)")
    with open("exact_solution_ids.pickle", "wb") as fh:
        pickle.dump(chosen_ids, fh)
    print(f"saved {len(chosen_ids)} set ids to exact_solution_ids.pickle")
    return final_greys, 106 + final_greys, chosen_ids


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_optimal_2283"
    ps = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    ms = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    solve(name, ps, ms)
