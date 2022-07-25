""""
tokenize.py
Parses output from AWS ASR for the front of the pipeline
"""

# os utilities
import os
# pathing
import pathlib
# regex
import re
# glob
import glob
# argument
import argparse
# default dictionaries
from collections import defaultdict
# utility string punctuations
import string

# sentence tokenizer
from rpunct import RestorePuncts
# import nltk
from nltk import sent_tokenize
# handwavy tokenization
from nltk.tokenize import word_tokenize
from nltk import RegexpParser, pos_tag

targetfile = "/Users/houliu/Documents/Projects/talkbank-alignment/AWS/09.cha"

# one-liner to untokenize
untokenize = lambda tokens:"".join([" "+i if not i.startswith("'") and i!="na" and i!= "n't" and i not in string.punctuation else i for i in tokens]).strip()

"""
felflare/bert-restore-punctuation
"""

# restoration model
rpunct = RestorePuncts()

def utterance_tokenize(passage, rpunct):
    """Tokenize a passage into utterances

    Arguments:
        passage (str): the untokenized passage
        rpunct (RestorePuncts): an instance of the punctuation
                                restoration model
    """

    # perform punctuation
    sentence_punctuated = rpunct.punctuate(passage)
    # perform sentence tokenization
    sentence_tokenize = sent_tokenize(sentence_punctuated)

    # pos_tagging
    sentence_words = [word_tokenize(i) for i in sentence_tokenize]
    sentence_tagged = [[j[1] for j in pos_tag(i)] for i in sentence_words]
    # determine split locations
    split_locations = [[i for i, x in enumerate(j) if x == "CC"]
                    for j in sentence_tagged]
    # add the beginning and end locations
    split_locations = [[0]+j+[len(sentence_tagged[indx])]
                    for indx, j in enumerate(split_locations)]
    # perform splitting
    split_sentences = [[sentence_words[indx][i[j]:i[j+1]]
                        for j in range(len(i)-1)
                        if len(sentence_words[indx][i[j]:i[j+1]]) > 0 ]
                    for indx, i in enumerate(split_locations)]

    # and untokenize the results + flatten the list
    untokenized_sentences = sum([[untokenize(j).replace(',', '') for j in i]
                                for i in split_sentences], []) #type: ignore

    # add a punctuation to the end if needed
    punctuated_sentences = [i
                            if i[-1] in ['?','.','!']
                            else i+'.'
                            for i in untokenized_sentences]
    # and format periods properly
    punctuated_sentences = [i[:-1]+" "+i[-1] for i in punctuated_sentences]

    return punctuated_sentences
