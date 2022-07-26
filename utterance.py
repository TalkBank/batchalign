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

# progress bar
from tqdm import tqdm

# import the tokenization engine
from utokengine import UtteranceEngine

# seed a utterance engine
E = UtteranceEngine("../../utterance-tokenizer/models/playful-lake-2")

TARGETFILE = "/Users/houliu/Documents/Projects/talkbank-alignment/AWS/MCI/09.cha"
OUTFILE = "/Users/houliu/Documents/Projects/talkbank-alignment/AWS/MCI/09.out.cha"

# read all chat files
def read_file(f):
    """Utility to read a single flo file

    Arguments:
        f (str): the file to read

    Returns:
        list[str] a string of results
    """
    
    # open and read file
    with open(f, 'r') as df:
        # read!
        lines = df.readlines()

    # coallate results
    results = []

    # process lines for tab-deliminated run-on lines
    for line in lines:
        # if we have a tab
        if line[0] == '\t':
            # take away the tab, append, and put back in results
            results.append(results.pop()+" "+line.strip())
        # otherwise, just append
        else:
            results.append(line.strip())

    # return results
    return results

# process a file
def process_file(f):
    # get lines in the file
    lines = read_file(f)

    # split by tier and crop info
    lines = [i.split("\t") for i in lines]

    # chop off end delimiters in main tier
    lines = [[i[0], i[1][:-2]] if i[0][0]=='*' else i for i in lines] 

    # get tiers seperated

    # array for header tiers
    header_tiers = []
    # pop out header tiers
    while lines[0][0][0] == '@':
        header_tiers.append(lines.pop(0))

    # array for main tiers
    main_tiers = []
    # pop out main tiers
    while lines[0][0][0] == '*':
        main_tiers.append(lines.pop(0))

    # and set the rest to closing
    closing_tiers = lines

    # process main tiers
    main_tiers_processed = []

    # for every line, process
    for line in main_tiers:
        # split the line
        line_split = line[1].split(" ")
        # pair them up
        line_paired = [(line_split[i],
                        line_split[i+1])
                    for i in range(0,len(line_split), 2)]
        # and fix the right end
        bullet_extract = lambda x: [int(i)
                                    for i in
                                    re.sub(r".(\d+)_(\d+).", r"\1|\2", x).split('|')]
        line_extracted = [[i[0], bullet_extract(i[1])] for i in line_paired]

        # append results
        main_tiers_processed.append((line[0], line_extracted))

    return header_tiers, main_tiers_processed, closing_tiers

# global realignment function
def retokenize(infile, outfile, utterance_engine):
    """Function to retokenize an entire chat file

    Attributes:
        infile (str): in .cha file
        outfile (str): out, retokenized out file
        utterance_engine (UtteranceEngine): trained utterance engine instance

    Used for output side effects
    """

    header, main, closing = process_file(infile)

    # collect retokenized lines
    realigned_lines = []

    # for each line, perform analysis and append
    for line in tqdm(main):

        # save the speaker for use later
        speaker = line[0]

        # we will now use UtteranceEngine to redo
        # utterance tokenization

        # extract words and bullets
        words, bullets = zip(*line[1])
        # build a giant string for passage
        passage = " ".join(words)
        # chunk the passage into utterances
        chunked_passage = utterance_engine(passage)
        # remove the end delimiters (again!) because
        # all we case about here are the split utterances
        # we will add "." later
        chunked_passage = [re.sub(r'([.?!])', r'', i)
                        for i in chunked_passage]
        # split the passage align to realign with the bullets
        # that was previously provided. we do a len() here
        # because all we really need is the index at which
        # the first and last bullet of the line exists
        chunked_passage_split = [len(i.split(' ')) for i in chunked_passage]
        # tally up to create zipped result
        chunked_passage_split = [0]+[sum(chunked_passage_split[:i+1])
                                for i in range(len(chunked_passage_split))]
        # we subtract one from each element to calculate the stop index
        chunked_passage_split_subtract = [i-1 for i in chunked_passage_split][1:]
        # and now, pair one-off-shift groups: this is the IDs of the start
        # and stop times we look for each utterance's new bullet
        shifts = list(zip(chunked_passage_split, chunked_passage_split_subtract))
        # finally, lookup the actual bullet values
        new_bullets = [(bullets[i[0]][0], bullets[i[1]][1]) for i in shifts]



        # we will stringify it into new bullets
        new_bullets_str = [f'{i[0]}_{i[1]}' for i in new_bullets]

        # and finally, we can construct the final line
        # speaker, tab, sentence, end of sentence mark, end bullet
        realigned_lines = realigned_lines + [speaker+'\t'+i[0]+' . '+i[1]
                                            for i in zip(chunked_passage, new_bullets_str)]

    # realign header and closing
    realigned_header = ['\t'.join(i).strip() for i in header]
    realigned_closing = ['\t'.join(i).strip() for i in closing]

    # new chat file
    new_chat = ["@UTF8"]+realigned_header+realigned_lines+realigned_closing

    # and finally, synthesize
    with open(outfile, 'w') as df:
        # write!
        df.writelines([i+'\n' for i in new_chat])
