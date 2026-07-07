"""
Render a solved ALLSETS pickle into a human-readable, game-playable path
(the format of result.txt).

A solution is a *connected* set of 4-letter words. Because `undo` is free, we
can walk a spanning tree of that set in (size - 1) real operations: every word
is reached exactly once by a forward move, and backtracking to a branch point
costs nothing. This script performs that depth-first walk and prints:

    WORD n      forward move; n = running operation count. UPPERCASE = picture word.
    >word n     an undo (free). One '>' per undo step; n stays the same.

The walk starts from the game's forced opening WORM -> WORD -> WARD -> DRAW.

Usage:
    python3 render_solution.py                                  # default pickle -> stdout
    python3 render_solution.py "ALLSETS 173 alt.pickle"         # -> stdout
    python3 render_solution.py "ALLSETS 173 alt.pickle" out.txt # -> file
"""
import sys
import pickle
from common import find_all_branches, KEYWORDS, Set  # Set is needed to unpickle ALLSETS

# The game's forced opening.
OPENING_ROOT = "worm"
FORCED_NEXT = {"worm": "word", "word": "ward", "ward": "draw"}


def solution_words(allsets):
    """The solution is the union of the words in every PINK (committed) set."""
    words = set()
    for s in allsets.values():
        if s.isKey:
            words |= s.words
    return words


def build_adjacency(words):
    """Undirected graph over `words`: an edge means the two words are one game move
    apart (differ by a single letter, or are anagrams)."""
    words = set(words)
    return {w: sorted(b for b in find_all_branches(w) if b in words) for w in words}


def render(words):
    """Return (list_of_lines, total_operations) for the annotated path."""
    words = set(words)
    adj = build_adjacency(words)

    missing = KEYWORDS - words
    if missing:
        raise SystemExit(f"not a valid solution: {len(missing)} picture words are absent "
                         f"(e.g. {sorted(missing)[:8]})")
    if OPENING_ROOT not in words:
        raise SystemExit(f"opening word '{OPENING_ROOT}' is not in the solution set")

    label = lambda w: w.upper() if w in KEYWORDS else w
    lines = []
    visited = {OPENING_ROOT}
    stack = [OPENING_ROOT]
    op = 0

    lines.append(f"{label(OPENING_ROOT)} 0")

    def ordered_children(node):
        kids = [c for c in adj[node] if c not in visited]
        nxt = FORCED_NEXT.get(node)
        if nxt in kids:                # honour the forced opening moves
            kids.remove(nxt)
            kids.insert(0, nxt)
        return kids

    sys.setrecursionlimit(10 * len(words) + 1000)

    def dfs(node):
        nonlocal op
        node_depth = len(stack) - 1    # `node` sits here for the whole call
        for child in ordered_children(node):
            if child in visited:       # became visited via another branch (a cycle edge)
                continue
            # backtrack (free undos) from wherever we are down to `node`
            k = 0
            while len(stack) - 1 > node_depth:
                stack.pop()
                k += 1
                lines.append(f"{'>' * k}{label(stack[-1])} {op}")
            # forward move to the new word (+1 operation)
            op += 1
            lines.append(f"{label(child)} {op}")
            visited.add(child)
            stack.append(child)
            dfs(child)

    dfs(OPENING_ROOT)

    if len(visited) != len(words):
        unreached = sorted(words - visited)
        raise SystemExit(f"solution set is not connected: {len(unreached)} words are unreachable "
                         f"from '{OPENING_ROOT}' (e.g. {unreached[:8]})")
    return lines, op


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "ALLSETS 173 alt.pickle"
    with open(src, "rb") as handle:
        allsets = pickle.load(handle)

    lines, ops = render(solution_words(allsets))
    text = "\n".join(lines) + "\n"

    if len(sys.argv) > 2:
        with open(sys.argv[2], "w") as f:
            f.write(text)
        print(f"wrote {sys.argv[2]}: {ops} operations")
    else:
        sys.stdout.write(text)
