"""Small shared helpers: pickle load/save and logging."""
import pickle
import time


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
