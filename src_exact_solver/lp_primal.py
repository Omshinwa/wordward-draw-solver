"""Strong lower bound + strong feasible solution from the directed-cut LP.

Runs the directed (bidirected) cut LP relaxation with max-flow cut generation to
convergence -- that objective is a valid lower bound on #greys. The LP is nearly
integral, so its grey values also tell us which greys the optimum wants: we round
them into a feasible tree with LP-guided shortest-path routing.

Prints:  operations >= 106 + LP_bound   (lower bound)
         operations  = 106 + primal      (a real, playable solution)
"""
import sys
import time
import pickle
from collections import deque

import highspy

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)                                  # sibling exact-solver modules
sys.path.insert(0, os.path.join(_HERE, os.pardir, "src"))  # word_set, utils
from exact_solver import build_graph, Dinic  # noqa: E402
from heuristic import grow_tree, prune, greys_of  # noqa: E402

INF = highspy.kHighsInf


def build_lp(n, is_term, edges):
    """HiGHS arc LP: node arcs 0..n-1 (grey cost 1), then 2 link arcs / edge."""
    m = len(edges)
    node_var = list(range(n))
    link_var = [(n + 2 * k, n + 2 * k + 1) for k in range(m)]
    h = highspy.Highs()
    h.setOptionValue("output_flag", False)
    for v in range(n):
        h.addCol(0.0 if is_term[v] else 1.0, 0.0, 1.0, 0, [], [])
    for _ in range(2 * m):
        h.addCol(0.0, 0.0, 1.0, 0, [], [])
    return h, node_var, link_var


def lp_bound_and_values(name="graph_optimal_2283", time_budget=240.0, verbose=True):
    ids, idx, n, is_term, adj, edges, g = build_graph(name)
    terms = [i for i in range(n) if is_term[i]]
    root = terms[0]
    others = terms[1:]
    h, node_var, link_var = build_lp(n, is_term, edges)
    dinic = Dinic(n, edges, node_var, link_var)
    src = 2 * root + 1
    added = set()

    def add_cut(vs):
        if not vs:
            return False
        key = frozenset(vs)
        if key in added:
            return False
        added.add(key)
        h.addRow(1.0, INF, len(vs), list(vs), [1.0] * len(vs))
        return True

    def separate(x):
        dinic.set_caps(x)
        c = 0
        for t in others:
            if dinic.maxflow(src, 2 * t, cutoff=1.0) < 1.0 - 1e-6:
                c += add_cut(dinic.cut_vars(dinic._reach_from(src)))
                back = dinic._reach_to(2 * t)
                c += add_cut(dinic.cut_vars(bytearray(1 - b for b in back)))
        return c

    t0 = time.time()
    prev, stall = -1.0, 0
    rnd = 0
    x = None
    while True:
        h.run()
        x = h.getSolution().col_value
        lb = h.getObjectiveValue()
        c = separate(x)
        rnd += 1
        if verbose and (rnd % 10 == 0 or c == 0):
            print(f"  [LP {rnd}] bound={lb:.3f}  cuts+={c}  total={len(added)}  "
                  f"({time.time()-t0:.1f}s)")
        if c == 0:
            print(f"  [LP] converged: bound={lb:.4f}")
            break
        stall = stall + 1 if lb <= prev + 1e-4 else 0
        prev = lb
        if stall >= 30 or time.time() - t0 > time_budget:
            print(f"  [LP] stop (stall/budget) at bound={lb:.3f}")
            break
    lb = h.getObjectiveValue()
    return ids, n, is_term, adj, terms, root, x, lb, g


def round_primal(n, is_term, adj, terms, root, lpx, tries_frac=0.02):
    """LP-guided rounding: route SPH with cost (1 - lp value) so the tree hugs the
    LP's chosen greys; also plain SPH. Return the best (fewest greys) tree."""
    best = None
    best_g = 10 ** 9

    def consider(tree, tag):
        nonlocal best, best_g
        prune(n, is_term, adj, tree)
        gc = len(greys_of(n, is_term, tree))
        if gc < best_g:
            best_g = gc
            best = bytearray(tree)
        return gc

    # LP-guided weights: greys the LP likes are ~cheap, others ~1
    w_lp = [0.0 if is_term[v] else max(tries_frac, 1.0 - lpx[v]) for v in range(n)]
    w_plain = [0.0 if is_term[v] else 1.0 for v in range(n)]

    results = {}
    for start in terms:
        for tag, w in (("lp", w_lp), ("plain", w_plain)):
            tree = grow_tree(n, is_term, adj, terms, start, weight=w)
            gc = consider(tree, tag)
            results.setdefault(tag, []).append(gc)
    return best, best_g


def solve(name="graph_optimal_2283"):
    ids, n, is_term, adj, terms, root, lpx, lb, g = lp_bound_and_values(name)
    print(f"\nLP lower bound: {lb:.4f} greys  ->  operations >= {106 + lb:.4f} "
          f"(>= {int(-(-lb // 1)) + 106} integer)")

    t = time.time()
    tree, greys = round_primal(n, is_term, adj, terms, root, lpx)
    print(f"rounded primal: {greys} greys  ->  operations = {106 + greys}  "
          f"({time.time()-t:.1f}s)")

    lb_int = -(-lb // 1)  # ceil
    print(f"\n=> operations in [{int(106 + lb_int)}, {106 + greys}]  (record was 173)")
    chosen = [ids[v] for v in range(n) if tree[v]]
    with open("exact_solution_ids.pickle", "wb") as fh:
        pickle.dump(chosen, fh)
    print(f"saved {len(chosen)} set ids (primal) to exact_solution_ids.pickle")
    return lb, greys, chosen


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "graph_optimal_2283"
    solve(name)
