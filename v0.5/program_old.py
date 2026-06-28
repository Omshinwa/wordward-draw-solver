def FINAL_PATH_ULTRA(start):
    # does its best
    global chemin

    def find_shortest_path3(start, list_of_words):
        global chemin
        tree = {}
        if len(list_of_words) == 0 :
            return []
        
        todo = list_of_words.copy()

        while (len(todo) > 0): # or step < 500

            #### force quiz to be the last word?
            # if "quiz" in todo:
            #     for index, worz in enumerate(todo):
            #         if worz == "quiz":
            #             todo.pop(index)

            end = word_with_highest_profit(chemin[-1], todo)

            path = find_shortest_path(chemin[-1], end)
            for index, worz in enumerate(todo):
                if worz == end:
                    todo.pop(index)
            chemin = chemin + path

        
        # path = find_shortest_path(chemin[-1], "quiz")
        # chemin = chemin + path

    #
    #   using an euristic eval (*profit*) function, return the word with the biggest *profit*
    #   which will be the next picture word to go to
    #
    #   the current euristic uses the dynamic mean and dynamic variance
    #
    def word_with_highest_profit(start, todo=list_of_words_to_go_through):

        max_var = -999
        min_step_key = []

        for index, value in enumerate(pairs_data[word_to_id[start]+1]):
            key = pairs_data[0][index]
            if index>0 and value!='':
                if key not in todo:
                    continue
                mean = average_of(key, todo)
                # profit = mean - float(value) - (variance_of(key, mean, todo))

                profit = mean - float(value) - (variance_of_static(key)/4) #202

                if profit > max_var:
                    max_var = profit
                    min_step_key= [ key ]
                elif profit == max_var:
                    min_step_key.append( key )

        # return min_step_key[0] #kill it early

        # in the scenario of a tie for the eval function:
        
        if len(min_step_key)==1:
            return min_step_key[0]
        elif len(min_step_key)>1:
            max_var = -999
            max_var_key = None

            for key in min_step_key:
                profit = - float(value)
                if profit >= max_var:
                    max_var = profit
                    max_var_key = key
            return max_var_key

        else:
            raise ValueError ("No key found")

    
    find_shortest_path3(start, list_of_words_to_go_through)
    write_final_path(chemin)