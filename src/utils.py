"""Small shared helpers: pickle load/save, logging, and the word-move operations."""
import pickle
import time
from itertools import permutations

from word_set import dictionary


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
    valid_permutation = set()
    list_permutation = set([''.join(p) for p in permutations(word)])
    for permutation in list_permutation:
        if permutation in dictionary:
            valid_permutation.add(permutation)
    return valid_permutation


def find_all_substitution(word) -> set[str]:
    "The valid words reachable by swapping a single letter of <word>."
    valid_sub = set()
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for index in range(len(word)):
        for letter in alphabet:
            substitution = word[:index] + letter + word[index+1:]
            if substitution in dictionary:
                valid_sub.add(substitution)
    return valid_sub


def find_all_branches(word) -> set[str]:
    "Every word one legal move (substitution or anagram) away from <word>."
    return find_all_substitution(word) | find_all_permutation(word)
