This project tries to 'solve' the word game wordward-draw hosted at:

https://managore.itch.io/wordward-draw

Here's the rules of the game:

You start at a 4 letter specific word (in the game, we start with the words WORM -> WORD -> WARD)
You can move between words only with two operations:
    * You can change 1 letter of your current word
    * You can rearrange all the letters

eg: WORD -> WARD (changed the letter O to A)
eg: WARD -> DRAW

There's a set of valid 4 letters words (defined in `./dictionary.csv`)
You have a list 105 words to reach (defined in `./all_picture_words.txt`)


The goal of the game is to r
