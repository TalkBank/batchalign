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

# import nltk
from nltk import sent_tokenize
# handwavy tokenization
from nltk.tokenize import word_tokenize
from nltk import RegexpParser, pos_tag

targetfile = "/Users/houliu/Documents/Projects/talkbank-alignment/AWS/09.cha"



