"""Small shared helpers: pickle load/save, logging, and the word-move operations."""
import pickle
import time
from itertools import permutations
from string import ascii_lowercase

from word_set import DICTIONARY_WORDS


def load(name):
    "Load and return the object pickled in <name>.pickle."
    with open(name + ".pickle", "rb") as handle:
        return pickle.load(handle)


def save(obj, name):
    "Pickle <obj> into <name>.pickle."
    with open(name + ".pickle", "wb") as handle:
        pickle.dump(obj, handle, protocol=pickle.HIGHEST_PROTOCOL)


def log(msg):
    "Print <msg> and append it to log.txt."
    print(msg)
    with open("log.txt", "a") as file:
        file.write(msg)
        file.write("\n")


def test_time(callback):
    "Run <callback> and print how long it took."
    start = time.time()
    callback()
    print("--- %s seconds ---" % (time.time() - start))


def find_all_permutation(word) -> set[str]:
    "The valid words reachable by anagramming <word>."
    permutations_ = {''.join(p) for p in permutations(word)}
    return permutations_ & DICTIONARY_WORDS


def find_all_substitution(word) -> set[str]:
    "The valid words reachable by swapping a single letter of <word>."
    substitutions = {word[:i] + letter + word[i+1:]
                     for i in range(len(word)) for letter in ascii_lowercase}
    return substitutions & DICTIONARY_WORDS


def find_all_branches(word) -> set[str]:
    "Every word one legal move (substitution or anagram) away from <word>."
    return find_all_substitution(word) | find_all_permutation(word)
