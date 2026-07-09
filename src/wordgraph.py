"""The word graph.

A `WordGraph` holds every dictionary word as a `Set`, connected to the words one
game move away, plus a cache of each Set's distance to the reachable PINK
(solution) Sets. A Set is PINK when it contains a picture word or has been
committed to the solution (`Set.isKey`), and GREY otherwise.

This module owns the *state* and the operations on it. The reductions that shrink
the graph live in `reductions.py`, and the heuristic search in `solver.py`.
"""
from word_set import KEYWORDS, dictionary, Set
from utils import load, save, log, find_all_branches


class WordGraph:
    def __init__(self, sets=None):
        self.sets = sets if sets is not None else {}   # {word_id: Set}
        self.dist_to_pinks = {}                          # {set_id: {pink_id: distance}}

    # -------------------------------------------------------------- build / io
    @classmethod
    def from_dictionary(cls):
        "Build the initial graph: one singleton Set per dictionary word."
        branches = {}
        for i, word in enumerate(dictionary):
            b = find_all_branches(word)
            b.remove(word)
            branches[word] = b
            if (i + 1) % 500 == 0:
                print(i + 1)
        sets = [Set({word}, branches[word]) for word in branches]
        return cls({s.id(): s for s in sets})

    @classmethod
    def load(cls, name="graph"):
        "Load the sets dict from <name>.pickle into a new WordGraph."
        return cls(load(name))

    def save(self, name="graph"):
        "Pickle the sets dict to <name>.pickle (dist_to_pinks is a cache, saved separately)."
        save(self.sets, name)

    # -------------------------------------------------------------- queries
    def find(self, word):
        "The Set containing <word>, or None."
        for s in self.sets.values():
            if word in s.words:
                return s
        return None

    def pinks(self):
        "The PINK (in-solution) Sets as {id: Set}."
        return {k: s for k, s in self.sets.items() if s.isKey}

    def greys(self):
        "The GREY (optional) Sets as {id: Set}."
        return {k: s for k, s in self.sets.items() if not s.isKey}

    def words(self):
        "Every word across every Set."
        result = set()
        for s in self.sets.values():
            result |= s.words
        return result

    def cost(self):
        "(all words in PINK sets, count of non-picture words in PINK sets)."
        pinks = self.pinks().values()
        words = set()
        for s in pinks:
            words |= s.words
        return (words, sum(s.cost() for s in pinks))

    def is_winnable(self):
        "True while every picture word is still reachable inside the PINK sets."
        reachable = set()
        pinks = self.pinks()
        for pink in pinks.values():
            if len(pink.links) == 0 and len(pinks) > 1:
                log(f"PINK set {pink} can no longer be reached.")
                return False
            reachable |= pink.words
        if all(w in reachable for w in KEYWORDS):
            return True
        log("Not all picture words are reachable in the PINK sets.")
        return False

    def check_ids(self):
        "Sanity check: every Set must be keyed by its own id()."
        for key, s in self.sets.items():
            if key != s.id():
                print(f"ERROR key: {key}, id:{s.id()} for {s}")

    def to_txt(self):
        "Write the flat word list to KEYWORDS-<n>.txt."
        result = "\n".join(self.words())
        with open("KEYWORDS-" + str(len(result.split("\n"))) + ".txt", "w") as file:
            file.write(result)

    # -------------------------------------------------------------- mutation
    def remove(self, word, doPrint=True):
        "Delete the Set keyed <word>, its dist_to_pinks entry, and any links to it."
        words = self.sets[word].words
        del self.sets[word]

        if word in self.dist_to_pinks:
            del self.dist_to_pinks[word]
            if doPrint:
                log(f"  removed {word} from dist_to_pinks")

        for w in words:
            for s in self.sets.values():
                if w in s.links:
                    if doPrint:
                        print(f"removed {w} from {s}'s links")
                    s.links.remove(w)

    # -------------------------------------------------------------- distances
    def calculate_dist_to_pinks(self, save_result=False):
        """(Re)build dist_to_pinks: from every Set, the distance to each PINK it can
        reach without passing through another PINK. Slow.

        Two modes: while every GREY is still a singleton the distance is just the
        step count ("simple"); once GREYs hold several words it accumulates cost()."""
        if all(len(s.words) == 1 for s in self.greys().values()):
            mode = "simple"
        else:
            mode = "hard"

        self.dist_to_pinks = {}
        i = 0
        for key, SET in self.sets.items():
            i += 1
            if i % 100 == 0:
                print(f"setting {SET}'s pink links")
            tree = {key: False}
            links = {key: self.sets[key].cost()}
            step = 0

            progressing = True
            while progressing:
                progressing = False
                step += 1
                buffer = {}
                for set_id in tree:
                    if not tree[set_id]:
                        progressing = True
                        for link in self.sets[set_id].links:
                            if mode == "hard":  # accumulate GREY costs
                                if link not in links:
                                    links[link] = links[set_id] + self.sets[link].cost()
                                elif links[link] > links[set_id] + self.sets[link].cost():
                                    links[link] = links[set_id] + self.sets[link].cost()
                                if link not in tree and not self.sets[link].isKey:
                                    buffer[link] = False
                            else:               # only record PINK step counts
                                if self.sets[link].isKey:
                                    if link not in links:
                                        links[link] = step + 1
                                    elif links[link] > step + 1:
                                        links[link] = step + 1
                                elif link not in tree:
                                    buffer[link] = False
                        tree[set_id] = True
                tree.update(buffer)

            if mode == "hard":  # drop the non-PINK entries
                for link in list(links):
                    if link in tree:
                        del links[link]

            del links[key]
            self.dist_to_pinks[key] = links

        if save_result:
            save(self.dist_to_pinks, "dist_to_pinks")

    def pink_costs(self):
        """Reverse of dist_to_pinks: {pink_id: {origin_id: cost}} — for each PINK,
        the cost to reach it from every Set that can."""
        pink_cost = {}
        for origin, links in self.dist_to_pinks.items():
            for destination, link_cost in links.items():
                pink_cost.setdefault(destination, {})[origin] = link_cost
        return pink_cost

    def pink_cost_sort(self, pink_only=False):
        "PINK ids ordered by average cost-to-reach, cheapest first."
        pink_cost = self.pink_costs()
        averages = {}
        for pink in pink_cost:
            total = 0
            population = 0
            for link in pink_cost[pink]:
                if link not in self.sets:
                    log(f"  Cant find {link} in sets, deleting dist_to_pinks[{link}][{pink}]")
                    del self.dist_to_pinks[link][pink]
                elif not pink_only or self.sets[link].isKey:
                    population += 1
                    total += pink_cost[pink][link]
            averages[pink] = total / population
        return sorted(averages.items(), key=lambda item: item[1])

    def shortest_paths(self, start_set, end_set):
        """Every Set lying on a shortest path between two Set ids (used by
        delete_hard_greys)."""
        if start_set == end_set:
            return set()

        tree = {start_set: {"step": 0, "searched": False}}
        step = 0
        while end_set not in tree and step < 100:
            step += 1
            to_add = {}
            for set_id in tree:
                if not tree[set_id]["searched"]:
                    for link in self.sets[set_id].links:
                        if link not in tree and link not in to_add:
                            to_add[link] = {"step": step, "searched": False, "parents": {set_id}}
                        elif link in to_add:
                            if to_add[link]["step"] == step:
                                to_add[link]["parents"].add(set_id)
                        elif link in tree:
                            if tree[link]["step"] == step:
                                tree[link]["parents"].add(set_id)
            tree.update(to_add)
            tree[set_id]["searched"] = True

        if step == 100:
            raise TimeoutError("no path found")

        set_of_words = {end_set}
        frontier = {end_set}
        while start_set not in set_of_words:
            buffer = set()
            for parent in frontier:
                set_of_words.update(tree[parent]["parents"])
                buffer.update(tree[parent]["parents"])
            frontier = buffer
        return set_of_words
