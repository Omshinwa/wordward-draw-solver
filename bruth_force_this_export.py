import pickle
from common import find_all_branches, Word
from a_program_to_beat_cam import write_DICT_to_csv
#export stuff#

def export_ALLSETS_to_dict():
    
    with open("ALLSETS.pickle", 'rb') as handle:
        set_of_words = pickle.load(handle)

    TODO = list(set_of_words.values())[0].words

    step = 0
    DICT = { "worm": Word("worm", ""), "word":Word("word", ""), "ward":Word("ward", ""), "draw":Word("draw", "") }

    # #remove all starting words from the list of words to search
    for word in DICT:
        TODO.remove(word)

    while len(TODO)>0:
        print( "[" + str(len(DICT)) + "]" )

        SomethingHappened = False
        for CURRENTWORD in DICT.values():
            if not CURRENTWORD.propagated:
                SomethingHappened = True
                break
        
        if not SomethingHappened:
            input("Seems like the whole tree has been done but the program is still going?")

        smallDict = {}
        
        list_of_words = find_all_branches(CURRENTWORD.word)
        for word in list_of_words:
            if word not in [item.word for item in DICT.values()] and word in TODO:
                smallDict[word] = (Word(word, CURRENTWORD.word))
                CURRENTWORD.children.add(word)
                TODO.remove(word)
                             
        CURRENTWORD.propagated = True
        DICT.update( smallDict )
        # SET = newSET.copy()
        step += 1

    ######
    return DICT

write_DICT_to_csv(export_ALLSETS_to_dict())