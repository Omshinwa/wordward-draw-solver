"""The optimality-preserving reductions that shrink the graph before the
heuristic search, plus the fixpoint driver `optimize_all`.

Each takes a `WordGraph` and mutates it in place. Every reduction provably keeps
at least one optimal solution, so the reduced instance has the same optimum as
the original — see the README for the argument behind each one.
"""
import copy
from utils import log


def merge_pink_sets(g):
    "Contract adjacent PINK sets into one (both are in the solution anyway)."
    changed = True
    while changed:
        changed = False
        for key, s in g.sets.items():
            if s.isKey:
                for link in s.links:
                    if g.sets[link].isKey:
                        log(f"  pink: merged {g.sets[link]} with {s}")
                        first, second = sorted([g.sets[link].id(), s.id()])
                        g.merge_into(first, second)
                        changed = True
                        break
                if changed:
                    break


def clean_graph(g):
    "Drop links that point at Sets which no longer exist (a consistency sweep)."
    done = set()
    changed = True
    while changed:
        changed = False
        for key, s in g.sets.items():
            if key not in done:
                for word in s.links:
                    if word not in g.sets:
                        log(f"  cleaned {word} from {s}'s links")
                        s.links.remove(word)
                        changed = True
                        break
                if changed:
                    break
                done.add(key)


def delete_equivalent_greys(g, minimum_connection=1):
    """Drop dead GREYs (fewer than `minimum_connection` links) and GREYs dominated
    by another (their links are a subset of another GREY's)."""
    # dead ends first
    for grey in g.greys():
        if len(g.sets[grey].links) < minimum_connection:
            log("   deleted: " + g.sets[grey].id() + " (isolated)")
            g.remove(grey)

    greys = g.greys()
    count = 0
    for key, A in greys.items():
        count += 1
        if count % 100 == 0:
            print(f"checking {key}")
        for key2, B in greys.items():
            if A == B:
                continue
            if key not in g.sets or key2 not in g.sets:
                continue
            if (B.links - {A.id}).issubset(A.links - {B.id}):
                log("   subset deleted: " + B.id() + " is included in " + A.id())
                g.remove(key2)


def merge_greys(g):
    "Contract a chain of two degree-2 GREYs (reaching one forces passing the other)."
    done = set()
    changed = True
    while changed:
        changed = False
        greys = g.greys()
        for key, A in greys.items():
            if key not in done:
                if len(A.links) == 2:
                    for B in A.links:
                        if not g.sets[B].isKey and len(g.sets[B].links) == 2:
                            log(f"  grey: merged {A} with {B}")
                            g.merge_into(key, B)
                            changed = True
                            break
                    if changed:
                        break
                done.add(key)


def optimize_greys(g):
    log("   - OPTIMIZING GREYS -")
    log("       - MERGING GREYS-")
    merge_greys(g)
    log("       - DELETING EQUI-")
    delete_equivalent_greys(g)
    log("       - CLEANING (optional) -")
    clean_graph(g)


def optimize_all(g):
    "Run every reduction to a fixpoint (the size stops shrinking)."
    current = 0
    while current != len(g.sets):
        current = len(g.sets)
        log(f"  Currently {current} sets.")

        if not g.is_winnable():
            log("ERROR: the graph is no longer winnable; aborting reduction.")
            g.save("graph")
            return

        log("   - MERGING PINKS-")
        merge_pink_sets(g)

        log("   - find_necessary_sets -")
        find_necessary_sets(g)

        optimize_greys(g)

        if current == len(g.sets):
            log("   - delete_equi_greys_dist_to_pinks-")
            delete_equi_greys_dist_to_pinks(g)
            log("   - delete_hard_greys -")
            delete_hard_greys(g)


def delete_hard_greys(g):
    """Drop GREYs that never lie on a shortest path between two PINKs. Slow — it is
    effectively all-pairs shortest paths."""
    pinks = g.pinks()
    necessary = set()
    done = [set()]
    for A in pinks:
        for B in pinks:
            if A == B:
                continue
            if {A, B} in done:
                continue
            done.append({A, B})
            if len(done) % 100 == 0:
                print(f"searching for {A} and {B}, currently {len(necessary)} words")
            necessary.update(g.shortest_paths(A, B))

    for grey in g.greys():
        if grey not in necessary:
            log(f"  removing unnecessary set {grey}")
            g.remove(grey)


def find_necessary_sets(g):
    """Promote GREYs that are forced: a PINK with a single neighbour forces that
    neighbour, and any GREY whose removal makes the game unwinnable is a cut point
    present in every solution. Slow."""
    for key, pink in g.pinks().items():
        if len(pink.links) == 1:
            g.sets[list(pink.links)[0]].isKey = True
            merge_pink_sets(g)

    greys = g.greys()
    sets_backup = copy.deepcopy(g.sets)
    dist_backup = copy.deepcopy(g.dist_to_pinks)
    index_backup = copy.deepcopy(g.word_to_set)
    cut_in_the_past = False

    i = 0
    while i < len(greys) - 1:
        key = list(sorted(greys))[i]
        SET = greys[key]
        g.remove(key, False)
        if g.is_winnable():
            if i % 100 == 0:
                print(f"No info on {SET}.")
            cut_in_the_past = True
            i += 1
        else:
            if cut_in_the_past:
                print(f"    maybe must keep {SET}")
                g.sets = copy.deepcopy(sets_backup)
                g.dist_to_pinks = copy.deepcopy(dist_backup)
                g.word_to_set = copy.deepcopy(index_backup)
                cut_in_the_past = False
            else:
                log(f"  MUST KEEP {SET}")
                g.sets = copy.deepcopy(sets_backup)
                g.dist_to_pinks = copy.deepcopy(dist_backup)
                g.word_to_set = copy.deepcopy(index_backup)
                g.sets[key].isKey = True
                merge_pink_sets(g)
                return
    log("      no necessary set found.")
    g.sets = copy.deepcopy(sets_backup)
    g.dist_to_pinks = copy.deepcopy(dist_backup)
    g.word_to_set = copy.deepcopy(index_backup)


def delete_equi_greys_dist_to_pinks(g):
    "Drop GREYs that are at least as far from every PINK as some other GREY."
    greys = g.greys()
    done = 0
    for keyA in greys:
        for keyB in greys:
            done += 1
            if keyA == keyB:
                continue
            if keyA not in g.sets or keyB not in g.sets:
                continue
            if done % 100000 == 0:
                print(f"{keyA}, {keyB} delete_equi_greys_dist_to_pinks")
            if all(link in g.dist_to_pinks[keyA] and g.dist_to_pinks[keyB][link] >= g.dist_to_pinks[keyA][link]
                   for link in g.dist_to_pinks[keyB]):
                log(f"  set deleted: {keyB} is worse than {keyA}")
                g.remove(keyB)
