"""Entry point for the wordward-draw solver.

    python3 src/solver.py         run the heuristic search from graph.pickle
    python3 src/solver.py init    rebuild the reduced search space from the dictionary

Run from the repo root (the .txt inputs and .pickle checkpoints live there).
See the README for the algorithm.
"""
import sys
import time
from word_set import dictionary
from utils import load, save, log
from wordgraph import WordGraph
from reductions import merge_pink_sets, optimize_all


def heuristic(g):
    """Guess-and-reduce. When no reduction fires, commit the most promising Set to
    the bottleneck PINK, then re-run every reduction. Repeat until solved."""
    while g.is_winnable() and len(g.pinks()) > 1 and g.cost()[1] < 90:
        log(f"Currently {len(g.sets)} sets & {len(g.words())} words:  {g.cost()}")

        # the PINK that is, on average, farthest from the others: the current bottleneck
        bottleneck = g.pink_cost_sort()[-1][0]
        # score each neighbouring Set by how many PINKs it sits near, minus its own cost
        scored = [(link, sum(max(0, 4 - d) ** 3 for d in g.dist_to_pinks[link].values()) - g.sets[link].cost())
                  for link in g.sets[bottleneck].links]
        best = sorted(scored, key=lambda x: x[1])[-1]

        log(f"heuristic: added {best} as Key")
        g.sets[best[0]].isKey = True
        merge_pink_sets(g)
        optimize_all(g)

        g.save("graph")

    if not g.is_winnable():
        log("No winnable solution was reached.")
    else:
        words, non_picture = g.cost()
        log(f"Solution found: {len(words)} words ({non_picture} non-picture).")
        g.save("graph")


def run_heuristic():
    "Load the reduced graph + distances, run the heuristic, save the result."
    start = time.time()

    g = WordGraph.load("graph")
    g.dist_to_pinks = load("dist_to_pinks")

    open("log.txt", "w").close()
    heuristic(g)

    log("--- %s seconds ---" % (time.time() - start))
    g.save("graph")


def build_from_scratch():
    """Start from every dictionary word and reduce to the ~2283-set search space.

    optimize_all() maintains dist_to_pinks only incrementally, so the stored
    distances drift (they stay too optimistic as Sets are deleted) and the
    distance-based prune under-fires. Recomputing them from scratch between rounds
    unlocks the missed deletions; iterate until stable. Slow (~2 min)."""
    start = time.time()
    open("log.txt", "w").close()

    log(f"initializing {len(dictionary)} words into singleton Sets...")
    g = WordGraph.from_dictionary()
    log(f"  {len(g.sets)} Sets.")

    log("reducing the search space (slow)...")
    previous = None
    while previous != len(g.sets):
        previous = len(g.sets)
        g.calculate_dist_to_pinks()
        optimize_all(g)
        log(f"  round complete: {previous} -> {len(g.sets)} Sets")

    g.save("graph")
    save(g.dist_to_pinks, "dist_to_pinks")
    log("--- reduced to %d Sets in %s seconds ---" % (len(g.sets), time.time() - start))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        build_from_scratch()
    else:
        run_heuristic()
