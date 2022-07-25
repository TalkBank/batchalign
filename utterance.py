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

from nltk.translate.chrf_score import sentence_chrf
# sentence tokenizer
from rpunct import RestorePuncts
# import nltk
from nltk import sent_tokenize

# we use a pretrained BERT for punctuation restoration
"""
felflare/bert-restore-punctuation
"""

# thing
sentence = "okay well cat decides to climb up a tree and gets on a branch that it can't come down from and then the little girl comes along and the dog comes along and they both see the ms can they get their father and the father climbs up the tree to try and get the cat you got two people stuck in a tree or two creatures stuck in the tree and the bird is watching all this and somebody calls the fire department and they come out with a ladder and they're they're going to get ready they're gonna they're gonna rescue these two end of story"

# restoration model
rpunct = RestorePuncts()

# perform punctuation
sentence_punctuated = rpunct.punctuate(sentence)
sentence_tokenize = sent_tokenize(sentence_punctuated)
sentence_tokenize

