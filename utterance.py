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
# import temporary file
import tempfile

# json utilities
import json

# import nltk
from nltk import sent_tokenize
# handwavy tokenization
from nltk.tokenize import word_tokenize
from nltk import RegexpParser, pos_tag

# progress bar
from tqdm import tqdm

# ui tools
from tkinter import *
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

# import the tokenization engine
from utokengine import UtteranceEngine

# silence huggingface
os.environ["TOKENIZERS_PARALLELISM"] = "FALSE" 

SPEAKER_TRANSLATIONS = {
    "p": ("Participant", "PAR"),
    "i": ("Investigator", "INV"),
    "c": ("Child", "CHI")
}

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
def process_chat_file(f):
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

# global realignment function (for rev.ai)
def process_json_file(f, interactive=False):
    """Process a RevAI text file as input

    Attributes:
        f (str): file to process
        interactive (bool): whether or not to prompt for speaker info
    """

    # open the file and read its lines
    with open(f, 'r') as df:
        data = json.load(df)

    # create array for total collected utterance
    utterance_col = []

    # for each utterance
    for utterance in data["monologues"]:
        # get a list of words
        words = utterance["elements"]
        # coallate words (not punct) into the shape we expect
        # which is ['word', [start_ms, end_ms]]. Yes, this would
        # involve multiplying by 1000 to s => ms
        words = [[i["value"], [round(i["ts"]*1000),
                                round(i["end_ts"]*1000)]] # the shape 
                for i in words # for each word
                    if i["type"] == "text" and
                    not re.match(r'<.*>', i["value"])] # if its text

        # concatenate with speaker tier and append to final collection
        utterance_col.append((utterance["speaker"], words))

    # get a list of speaker IDs
    speaker_ids = {i[0] for i in utterance_col} # this is a set!
    speakers = {}

    corpus = "corpus_name"

    # generate the speaker information, or
    # otherwise fill it out
    if interactive:

        speakers_filtered = []
        # filter 2 statements for each speaker needed
        # and then push
        for speaker in speaker_ids:
            speakers_filtered.append(list(filter(lambda x:x[0]==speaker, utterance_col))[:2])

        # prompt hello
        print("Welcome to interactive speaker identification!")
        print(f"You are working with sample {pathlib.Path(f).stem}.\n")

        # print out samples from speaker
        for indx, speaker in enumerate(speaker_ids):
            print(f"\033[1mSpeaker {speaker}\033[0m") 
            print("\n".join([" ".join([j[0] for j in i[1]]) for i in speakers_filtered[indx]]))
            print()

        # prompt for info
        for speaker in speaker_ids:
            # get info and handle error correction
            # get speaker info
            speaker_tier = None
            speaker_name = input(f"Please enter all/first letter of name of speaker {speaker} (i.e. Participant or P): ").strip()
            if len(speaker_name) == 1:
                translation = SPEAKER_TRANSLATIONS.get(speaker_name.lower(), '*')
                speaker_name = translation[0]
                speaker_tier = translation[1]
            # if we don't have first capital and spelt correctly
            while not (speaker_name[0].isupper() and "*" not in speaker_name):
                print("Invalid response. Please follow the formatting example provided.")
                speaker_name = input(f"Please enter name of speaker {speaker} (i.e. Participant): ").strip()
                if len(speaker_name) == 1:
                    translation = SPEAKER_TRANSLATIONS.get(speaker_name.lower(), '*')
                    speaker_name = translation[0]
                    speaker_tier = translation[1]
            # if we are not using on letter shortcut, prompt for tier
            if not speaker_tier:
                # get tier info
                speaker_tier = input(f"Please enter tier of speaker {speaker} (i.e. PAR): ")
                # if we don't have first capital and spelt correctly
                while not (speaker_tier.isupper() and "*" not in speaker_name):
                    print("Invalid response. Please follow the formatting example provided.")
                    speaker_tier = input(f"Please enter tier of speaker {speaker} (i.e. PAR): ").strip()
            # add to list
            speakers[speaker] = {"name": speaker_name, "tier": speaker_tier}
            print()
        # Name of the corpus
        corpus = input("Name of the corpus: ")

    else:

        # generate info
        for speaker in speaker_ids:
            # add to list
            speakers[speaker] = {"name": f"Speaker {speaker}", "tier": speaker}

    # go through the list and reshape the main tier
    utterance_col = [['*'+speakers[i[0]]["tier"]+":",
                    i[1]] for i in utterance_col]

    # create the @Participants tier
    participants_tier = ", ".join([v["tier"]+f" {v['name']}"
                                for k,v in speakers.items()])
    participants_tier = ["@Participants:", participants_tier]

    # create the @ID tiers and @ID tier string
    id_tiers = [f"eng|{corpus}|{v['tier']}|||||{v['name']}|||" for k,v in speakers.items()]
    id_tiers = [["@ID:",i] for i in id_tiers]

    # finally, create media tier
    media_tier = ["@Media:", f"{pathlib.Path(f).stem}, audio"]

    # assemble final header and footer
    header = [["@Begin"],
                ["@Languages:", "eng"],
                participants_tier,
                *id_tiers,
                media_tier]
    footer = [["@End"]]

    # return result
    return header, utterance_col, footer

# get text GUI
def interactive_edit(name, string):
    # create a new UI
    root = Tk(screenName=f"Interactive Fix")
    root.title(f"Interactively Fixing {name}")
    # create the top frame
    top = ttk.Frame(root, padding=5)
    top.grid()
    # label
    ttk.Label(top, text=f"Fixing {name}  ", font='Helvetica 14 bold').grid(column=0, row=0)
    ttk.Label(top, text="Use *** to seperate speakers, newlines to seperate utterances.").grid(column=1, row=0)
    # insert a textbox and place it
    text_box = ScrolledText(root, height=50, width=100, borderwidth=20, highlightthickness=0)
    text_box.grid(column=0, row=1)
    # and insert our fixit string
    def settext():
        text_box.delete(1.0, "end")
        text_box.insert("end", string)
    # create a finishing function
    settext()
    # create the bottom frame
    bottom = ttk.Frame(root, padding=5)
    bottom.grid()
    # don't stop until we do
    # this is a CHEAP MAINLOOP, but its used
    # to control when the text element can
    # be destroyed (i.e. not before reading)
    def stopit():
        # hide
        root.withdraw()
        # leave!
        root.quit()
    # create the buttons
    ttk.Button(bottom, text="Reset", command=settext).grid(column=0, row=0,
                                                           padx=20, pady=5)
    ttk.Button(bottom, text="Submit", command=stopit).grid(column=1, row=0,
                                                           padx=20, pady=5)
    # mainloop
    root.mainloop()
    final_text = text_box.get("1.0","end-1c")
    root.destroy()

    # return the new contents of the textbox
    return final_text

# global realignment function
def retokenize(infile, outfile, utterance_engine, interactive=False):
    """Function to retokenize an entire chat file

    Attributes:
        infile (str): in .cha or json file
        outfile (str): out, retokenized out file
        utterance_engine (UtteranceEngine): trained utterance engine instance
        interactive (bool): whether to enable midway user fixes to label data/train

    Used for output side effects
    """

    # if its json, use json the processor
    if pathlib.Path(infile).suffix == ".json": 
        header, main, closing = process_json_file(infile, interactive)
    # if its an AWS .cha (from Andrew), we will use the chat processor
    else:
        header, main, closing = process_chat_file(infile)

    # chunk the data with our model
    chunked_passages = []

    # for each line, create chunks
    for line in tqdm(main):
        # extract words and bullets
        words, bullets = zip(*line[1])
        # build a giant string for passage
        passage = " ".join(words)
        # we will now use UtteranceEngine to redo
        # utterance tokenization
        # chunk the passage into utterances
        chunked_passage = utterance_engine(passage)
        # remove the end delimiters (again!) because
        # all we case about here are the split utterances
        # we will add "." later
        chunked_passage = [re.sub(r'([.?!])', r'', i)
                        for i in chunked_passage]
        # append it to the chunked_passages
        chunked_passages.append(chunked_passage)

    # if we need to the interactive fixit program,
    # run the routine
    if interactive:
        # create the output string
        fixit_string = "\n\n***\n\n".join(["\n\n".join(i) for i in chunked_passages])

        # let the user edit the fixit string
        edited_text = [[j.strip() for j in i.split("\n\n")]
                    for i in interactive_edit(pathlib.Path(infile).stem,
                                            fixit_string).split("\n\n***\n\n")]

        # set the chunked passage back
        chunked_passages = edited_text

    # collect retokenized lines
    realigned_lines = []

    # for each line, perform analysis and append
    for line, chunked_passage in zip(main, chunked_passages):

        # save the speaker for use later
        speaker = line[0]

        # extract words and bullets
        _, bullets = zip(*line[1])
        # build a giant string for passage
        passage = " ".join(words)
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

