
# Pathing facilities
import pathlib

# I/O and stl
import os
from posixpath import expanduser
import random # for testing

# Import pathing utilities
import glob
from shutil import move
from typing import ContextManager
from typing_extensions import dataclass_transform

# XML facilities
import xml.etree.ElementTree as ET

# Also, include regex
import re

# Import a progress bar
from tqdm import tqdm

# Argument parser
import argparse

# defaultdict
from collections import defaultdict

from baln.eaf import eafinject

# silence OMP
os.environ["KMP_WARNINGS"] = "FALSE" 

# import utilities
from .utils import *
from .eaf import *

# mfa
from montreal_forced_aligner.command_line.align import run_align_corpus
from montreal_forced_aligner.command_line.g2p import run_g2p
from montreal_forced_aligner.command_line.validate import run_validate_corpus
from montreal_forced_aligner.models import ModelManager

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)
bullet = lambda start,end: f" {int(round(start*1000))}_{int(round(end*1000))}" # start and end should be float seconds

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=resolve_clan()
ATTRIBS_PATH=os.path.join(CURRENT_PATH, "./attribs.cut")

DISFLULENCY_CODE = re.compile("\[.*?\]")

# default MFA settings
def make_config_base():
    commands = argparse.Namespace()
    # we want to clean each time
    commands.clean = True
    # pathing
    commands.temporary_directory = ""
    commands.config_path = ""
    commands.speaker_characters = "0"

    return commands
    

# import textgrid
from .opt.textgrid.textgrid import Interval, TextGrid, IntervalTier

def align_directory_mfa(directory, data_dir, model=None, dictionary=None, beam=10):
    """Given a directory of .wav and .lab, align them

    Arguments:
        directory (string): string directory filled with .wav and .lab files with same name
        data_dir (string): output directory for textgrids
        [model (str)]: model to use
        [dictionary (str)]: dictionary to use
        [beam (int)]: beam width for initial MFA alignment

    Returns:
        none
    """

    defaultmodel = lambda x:os.path.join("~","mfa_data",x)
    defaultfolder = os.path.join("~","mfa_data")
    # make the path
    os.makedirs(os.path.expanduser(defaultfolder), exist_ok=True)

    # if models are not downloaded (signified by the note)
    if not os.path.isfile(os.path.expanduser(defaultmodel(".mfamodels"))):
        # create model manager
        manager = ModelManager()
        # download english models
        manager.download_model("g2p", "english_us_arpa", True)
        manager.download_model("acoustic", "english_us_arpa", True)
        manager.download_model("dictionary", "english_us_arpa", True)
        # create note file
        with open(os.path.expanduser(defaultmodel(".mfamodels")), "w") as df:
            df.write("")

    # define model
    if not model:
        acoustic_model = "english_us_arpa"
    else:
        acoustic_model = model # TODO

    # define dictionary path
    if not dictionary:
        dictionary = os.path.join(directory, 'dictionary.txt')

    # generate dictionary if needed
    if not os.path.exists(dictionary):
        commands = make_config_base()

        # here are the input and output paths
        commands.g2p_model_path = "english_us_arpa"
        commands.input_path = directory
        commands.output_path = dictionary

        # run mfa
        run_g2p(commands, [])

    # and finally, align!
    commands = make_config_base()
    # we want to run clean each time
    commands.NUM_JOBS = 8
    # i/o
    commands.temporary_directory = ""
    commands.corpus_directory = directory
    commands.dictionary_path = dictionary
    commands.acoustic_model_path = acoustic_model
    commands.output_directory = data_dir
    # settings
    commands.beam = beam
    commands.retry_beam = 100

    run_align_corpus(commands, [])
   
# Parse a TextGrid file for word tier
def parse_textgrid_long(file_path):
    """Parse a TextGrid file for the word tier

    Arguments:
        file_path (string): name of the TextGrid file

    Returns:
        a list of (((word, (start_time, end_time))... x number_words),
                   ((phoneme, (start_time, end_time))... x number_phones))
    """

    # Load files
    text_grid = TextGrid.fromFile(file_path)

    # Get tiers
    word = [i for i in text_grid if "words" in i.name]
    pho = [i for i in text_grid if "phones" in i.name]

    # Convert pho and word tiers
    word_tiers = [[(i.mark, (i.minTime, i.maxTime)) for i in j] for j in word]
    phone_tiers = [[(i.mark, (i.minTime, i.maxTime)) for i in j] for j in pho]

    # flatten word tiers and sort 
    word_tiers = sorted(sum(word_tiers, []), key=lambda x:x[1][0])
    phone_tiers = sorted(sum(phone_tiers, []), key=lambda x:x[1][0])

    # Skip all blanks (to reinsert spaces)
    word_tiers = list(filter(lambda x:x[0]!="", word_tiers))
    phone_tiers = list(filter(lambda x:x[0]!="", phone_tiers))

    # return the result
    return (word_tiers, phone_tiers)

def parse_textgrid_short(file_path):
    """Parse a TextGrid file for the word tier

    Arguments:
        file_path (string): name of the TextGrid file

    Returns:
        a list of ((word, (start_time, end_time))... x number_words)
    """

    # Open the file
    with open(file_path, "r") as df:
        content = df.readlines()

    # Clean up newlines and spaces
    content = [i.strip() for i in content]
    # Find the IntervalTier line
    enumerated_line = enumerate(content)
    enumerated_line = list(filter(lambda x:x[1]=='"IntervalTier"', enumerated_line))
    # The word tier is the second IntervalTier
    word_tier = enumerated_line[1][0]
    # We then cut the content to the word tier (skipping the top label and line count)
    content = content[word_tier+5:]
    # Then, we iterate through three-line chunks and append to the wordlist
    wordlist_alignments = []
    # For each of the wordlist
    for i in range(0, len(content), 3):
        # We skip any spaces
        if content[i+2] != '"sp"':
            # And append the words in paris
            wordlist_alignments.append((content[i+2][1:-1], (float(content[i]), float(content[i+1]))))

    return wordlist_alignments

# Align the alignments!
def transcript_word_alignment(elan, alignments, alignment_form="long", debug=False):
    """Align the output of parse_transcript and parse_textgrid_* together

    Arguments:
        elan (string): path of elan files
        alignments (string): path of parse_alignments
        alignment_form (string): long or short (MFA or P2FA textGrid)
        debug (bool): debug print mode

    Returns:
        {"alignments": ((start, end)...*num_lines), "terms": [bulleted results: string...*num_utterances], "raw": [(word/pause: (start, end)/None)]}
    """

    transcript = elan2transcript(elan)["transcript"]
    tiers = elan2transcript(elan)["tiers"]

    # Get alignment form
    if alignment_form == "long":
        aligned_words, _ = parse_textgrid_long(alignments)
    elif alignment_form == "short":
        aligned_words = parse_textgrid_short(alignments)
    else:
        raise Exception(f"unknown alignment_form {alignment_form}")

    # cleaned transcirpt
    unaligned_words = []
    unaligned_tiers = []
    sentence_starts = []
    sentence_ends = []
    
    # we perform cleaning and tokenization of the transcript
    # to create an unaligned word plate. This is used fro
    # matching against the aligned word

    # index becase we'll be doing a lot of shuffling
    i = 0

    # For each sentence
    for tier, current_sentence in zip(tiers, transcript):
        # remove extra delimiters
        current_sentence = current_sentence.replace("+","+ ")
        current_sentence = current_sentence.replace("$","$ ")
        current_sentence = current_sentence.replace("-","- ")
        current_sentence = current_sentence.replace("↫","↫ ")

        # split results
        splits = current_sentence.split(" ")

        # append boundaries
        sentence_starts.append(i)

        # we generate a cleaned and uncleaned match list
        for word in splits:
            cleaned_word = word.lower().replace("[/]","") # because of weird spacing inclusions
            cleaned_word = re.sub(r"&\*\w+: ?\w+", '', cleaned_word)
            cleaned_word = cleaned_word.replace("(","").replace(")","")
            cleaned_word = cleaned_word.replace("[","").replace("]","")
            cleaned_word = cleaned_word.replace("<","").replace(">","")
            cleaned_word = cleaned_word.replace("“","").replace("”","")
            cleaned_word = cleaned_word.replace(",","").replace("!","")
            cleaned_word = cleaned_word.replace("?","").replace(".","")
            cleaned_word = cleaned_word.replace("&=","").replace("&-","")
            cleaned_word = cleaned_word.replace("+","").replace("&","")
            cleaned_word = cleaned_word.replace(":","").replace("^","")
            cleaned_word = cleaned_word.replace("$","").replace("\"","")
            cleaned_word = cleaned_word.replace("&*","").replace("∬","")
            cleaned_word = cleaned_word.replace("-","").replace("≠","")
            cleaned_word = cleaned_word.replace(":","").replace("↑","")
            cleaned_word = cleaned_word.replace("↓","").replace("↑","")
            cleaned_word = cleaned_word.replace("⇗","").replace("↗","")
            cleaned_word = cleaned_word.replace("→","").replace("↘","")
            cleaned_word = cleaned_word.replace("⇘","").replace("∞","")
            cleaned_word = cleaned_word.replace("≋","").replace("≡","")
            cleaned_word = cleaned_word.replace("∙","").replace("⌈","")
            cleaned_word = cleaned_word.replace("⌉","").replace("⌊","")
            cleaned_word = cleaned_word.replace("⌋","").replace("∆","")
            cleaned_word = cleaned_word.replace("∇","").replace("*","")
            cleaned_word = cleaned_word.replace("??","").replace("°","")
            cleaned_word = cleaned_word.replace("◉","").replace("▁","")
            cleaned_word = cleaned_word.replace("▔","").replace("☺","")
            cleaned_word = cleaned_word.replace("♋","").replace("Ϋ","")
            cleaned_word = cleaned_word.replace("∲","").replace("§","")
            cleaned_word = cleaned_word.replace("∾","").replace("↻","")
            cleaned_word = cleaned_word.replace("Ἡ","").replace("„","")
            cleaned_word = cleaned_word.replace("‡","").replace("ạ","")
            cleaned_word = cleaned_word.replace("ʰ","").replace("ā","")
            cleaned_word = cleaned_word.replace("ʔ","").replace("ʕ","")
            cleaned_word = cleaned_word.replace("š","").replace("ˈ","")
            cleaned_word = cleaned_word.replace("ˌ","").replace("‹","")
            cleaned_word = cleaned_word.replace("›","").replace("〔","")
            cleaned_word = cleaned_word.replace("〕","")
            cleaned_word = re.sub(r"@.", '', cleaned_word)
            cleaned_word = re.sub(r"&.", '', cleaned_word)
            cleaned_word = re.sub(r"↫(.*)↫", r'', cleaned_word)
            cleaned_word = re.sub(r"↫", r'', cleaned_word)
            cleaned_word = cleaned_word.strip()

            if debug:
                print(word, cleaned_word)

            # append the cleaned and uncleaned versions of words 
            unaligned_words.append((word, cleaned_word, i))
            unaligned_tiers.append(tier)
            i += 1

        # append boundaries
        sentence_ends.append(i)
    
    # conform boundaries
    sentence_boundaries = list([list(range(i,j)) for i,j in zip(sentence_starts, sentence_ends)])

    # we now perform n-round alignment
    # essentially, for each word in the aligned section, we
    # match it to the easiest canidate in the unaligned words
    # to create the final transcript

    backplated_alignments = []
    aligned_indicies = []
    
    # for each word
    for aligned_word, (start, end) in aligned_words:

        # we will go through the unaligned results to find the earlist
        # available canidate

        # for each word
        for elem in unaligned_words:
            # unpack element
            word, cleaned_word, i = elem
            # if we can align, do align
            if cleaned_word == aligned_word: 
                backplated_alignments.append((i, word, (start, end)))
                # having used it, we remove it
                unaligned_words.remove(elem)
                # and push to tracker
                aligned_indicies.append(i)
                break

        # if cleaned_word != aligned_word: 
        #     print(f"'{cleaned_word}', '{aligned_word}'")
   
    # find missing elements
    to_reinsert = list(filter(lambda x:x[2] not in aligned_indicies, unaligned_words))
    to_reinsert = [(i[2], i[0], None) for i in to_reinsert]

    # sort and reincorporate backplated alignments
    backplated_alignments = sorted(backplated_alignments+to_reinsert, key=lambda i:i[0])

    # set the begin
    j = 0

    # for each tier, perform timestamp correction to prevent self-overlap talk
    # which MFA sometimes generates, as well as fix the issues with sudden unbulleted
    # words in the input

    # check if we need backtracking
    # (i.e. "we corrected an error, backpropegate")
    backtracking = False

    # begin a loop to scan and correct errors
    while j < len(backplated_alignments):
    # while False:

        # get the results 
        indx, word, interval = backplated_alignments[j]
        tier = unaligned_tiers[indx]

        if debug:
            print(indx, word, interval)

        # if we are at an unalignable word, we move on
        # if we are backtracking, skip over anything that's
        # not part of the tier to be backtracked
        if not interval and not backtracking:
            j += 1
            continue
        elif backtracking and ((not interval) or (tier != backtracking)) and j!= 0:
            j -= 1 
            continue
        # if we are backtracking, and we can't do anything
        elif backtracking and ((not interval) or (tier != backtracking)) and j == 0:
            j += 1
            backtracking = False
            continue

        # reset backtracking
        backtracking = False

        # if there is an interval, we unpack it and ensure
        # that a few things is the case
        start,end = interval

        # get the first remaining indexable elements
        rem = None
        remword = None
        i = indx+1

        # go through in a while loop until we found
        # the next indexable element
        while i<len(backplated_alignments) and ((not rem) or (unaligned_tiers[i] != tier)):
            rem = backplated_alignments[i][2]
            remword = backplated_alignments[i]
            i += 1

        # if end is after the next starting, set the end
        # to be the next starting
        if rem and end > rem[0]:
            if debug:
                print("BACK1", end, remword)
            end = rem[0]
            backtracking = tier # backprop to correct prev. errors

        # if end is smaller than start, conform start to be
        # a bit before end
        if start > end:
            if debug:
                print("BACK2", start, end)
            start = max(end, 0.0001)-0.0001
            backtracking = tier # backprop to correct prev. errors

        # if we are unalignable, give up. Otherwise, don't give up
        if abs(start-end) < 0.001:
            backplated_alignments[indx] = (indx, word, None)
        else:
            backplated_alignments[indx] = (indx, word, (start, end))

        # if don't need backprop, continue
        if backtracking:
            j -= 1
        # if we do need backtracking
        else:
            j += 1 

    # conform the sentences 
    backplated_alignments_sentences = [[backplated_alignments[j] for j in i] for i in sentence_boundaries]

    # generate final results
    results = [[(i[1], i[2]) for i in j] for j in backplated_alignments_sentences]

    # extract alignments
    results_filtered = [list(filter(lambda x:x[1], i)) for i in results]
    # if there is nothing to align, just produce (0,0)
    alignments = [(i[0][1][0], i[-1][1][1]) if len(i) > 0 else (0,0) for i in results_filtered]

    # recreate results
    bulleted_results = []
    # Convert bulleted results
    for sentence in results:
        # bullet the sentence
        sentence_bulleted = []
        # set indx = 0
        indx = 0
        # for each term
        while indx < len(sentence):
            # load the value
            i = sentence[indx]
            # if alignable and ends with a angle bracket or plus sign, put the bullet inside the bracket
            if i[1] and (i[0] != '' and (i[0][-1] == '>' or i[0][-1] == '+')):
                sentence_bulleted.append(i[0].strip()[:-1] + bullet(i[1][0], i[1][1]) + i[0].strip()[-1])
            # if alignable and ends with a dollar sign, put the next mark, then add the bullet
            elif i[1] and indx+1 < len(sentence) and i[0] != '' and i[0][-1] == '$':
                # get the cucrent expression, the next, then bullet
                cur = i[0].strip()
                indx += 1
                cur += sentence[indx][0]
                sentence_bulleted.append(cur + bullet(i[1][0], i[1][1]))
            # if alignable and ends with a square bracket, put the bullet after the last the bracket
            # TODO. Future editors, please accept my apologies for the following line.
            elif (i[1] and ((indx+1 < len(sentence) and sentence[indx+1][0] and sentence[indx+1][0][0] == '[') or (indx+2 < len(sentence) and sentence[indx+1][0] == "" and sentence[indx+2][0] and sentence[indx+2][0][0] == '['))) or (i[0] and i[0][0] == '['):
                # if "12033" in elan:
                #     print(i, sentence[indx+1])

                # get template result
                result = i[0].strip()
                # clear start and end
                start = None
                end = None
                # get start
                if i[1]:
                    start = i[1][0]
                    end = i[1][1]

                # while we are open, keep reading
                while (indx+1) < len(sentence):
                    # increment reading
                    indx += 1
                    # if no start, but have start now, set start
                    if not start and sentence[indx][1]:
                        start = sentence[indx][1][0]
                    # set end to the new end
                    if sentence[indx][1]:
                        end = sentence[indx][1][1]

                    # append result
                    result = result + " " + sentence[indx][0].strip()
                    # check if closed
                    if result[-1] == "]":
                        # if there's a next, and the next is not another open
                        if (indx+1 < len(sentence) and sentence[indx+1][0] != "" and sentence[indx+1][0][0] != "[") or indx+1 >= len(sentence):

                            break

                if start:
                    # append result
                    sentence_bulleted.append(result + bullet(start, end))
                else:
                    # append result without bullet
                    sentence_bulleted.append(result)
            # if alignable and next is a code, append the code first
            elif i[1] and indx+1 < len(sentence) and DISFLULENCY_CODE.match(sentence[indx+1][0]):
                sentence_bulleted.append(i[0] + " " + sentence[indx+1][0] + bullet(i[1][0], i[1][1]))
                indx += 1
            # if alignable and next is a repeat, append a bracket
            # and then the bullet
            elif i[1] and indx < len(sentence)-1 and sentence[indx+1][0] != "" and sentence[indx+1][0][0:2] == "[/":
                sentence_bulleted.append(i[0].strip() +
                                         " " +
                                         sentence[indx+1][0].strip() +
                                         bullet(i[1][0], i[1][1]))
                # also skip the next iteration as its already appended
                indx+=1 
            # else, just append the element and bullet
            elif i[1]:
                # appending the current word and chorresponding bullet
                sentence_bulleted.append(i[0].strip() + bullet(i[1][0], i[1][1]))
            else:
                sentence_bulleted.append(i[0])
            # increment
            indx += 1

        # replace sentence
        sentence = " ".join(sentence_bulleted).strip()

        ### Final Santy Checks and Shape Conformations ###
        # if you can insert proper logic, do so. If not, use
        # this area as the last-ditch preprocessing step to
        # make spontaneous final transcript adjustments happen
        
        # remove extra delimiters, as a final sanity check
        sentence = sentence.replace("+ ","+")
        sentence = sentence.replace("_ ","_")
        sentence = sentence.replace("- ","-")
        sentence = sentence.replace(" >",">")
        sentence = sentence.replace("< ","<")
        sentence = sentence.replace("$ ","$")
        sentence = sentence.replace("& ","&")
        sentence = sentence.replace("↫ ","↫")
        # however, double < should have a space between
        sentence = sentence.replace("<<","< <")
        sentence = sentence.replace("+<"," +< ")
        sentence = sentence.replace("[<]"," [<] ")

        # sentence = re.sub(r" +", " ", sentence)

        # concat and append to bulleted results
        bulleted_results.append(sentence.strip())

    # Return the fimal alignments
    return {"alignments": alignments, "terms": bulleted_results, "raw": results}

def disfluency_calculation(raw_results, tiers):
    """tool to help calculate disfluncy per utterance

    Attributes:
        raw_results: a list of [(word/pause: (start, end)/None)] representing
                     alignment
        tiers: tier information to seperate terms out
    """

    # sentence logs
    logs = []

    # for each utterance
    for tier, utterance in zip(tiers, raw_results):
        # create a default dict to track
        tracker = defaultdict(int)
        # the item logs
        # contents should be [(item, start, end)...xnum_marks]
        log = []

        # seed a for loop (so we can skip things) and iterate
        i = 0
        while i < len(utterance):
            # get the mark
            mark = utterance[i]

            # get timemark
            # if timemark exists, the beginning is counted
            # as the timeark. Otherwise, the end of the
            # previous one is the timemark

            if mark[1]:
                # start of the current one
                timemark = mark[1][0]
            elif i!=0 and utterance[i-1][1]:
                # end of the previous one
                timemark = utterance[i-1][1][1]
            else:
                timemark = None

            # if we have an empty line, we ignore
            if mark[0] == "": pass
            # if we have a retraction or repetition, we add it
            elif mark[0] == "[/]" or  mark[0] == "[//]" :
                # append the previous result to the log
                # for the timing
                log.append((mark[0], timemark))
                # and add one to the tracker
                tracker[mark[0]] += 1
            # if we have an ending utterance mark (at the end of uterances), we add it
            elif mark[0][-1]  == "]" and (i == len(utterance)-1):
                # append the result to the log
                log.append((mark[0][:-1], timemark))
                # and add one to the tracker
                tracker[mark[0][:-1]] += 1
            # if we have a filled pause or verbal disfluency
            elif mark[0] == "&+" or mark[0] == "&-":
                # append the result to log
                # by gettincg the start of the next item
                log.append((mark[0], utterance[i+1][1][0]))
                tracker[mark[0]] += 1
            # if we have a pause, also add it
            elif mark[0] == "(.)" or mark[0] == "(..)" or mark[0] == "(...)":
                # append the result
                log.append(("(.)", timemark))
                # and add one to the tracker
                tracker["(.)"] += 1

            # increment  
            i += 1

        # append log to logs
        logs = logs + log

    # Union the logs together
    # print(dict(tracker), log)

def do_align(in_directory, out_directory, data_directory="data", model=None, dictionary=None, beam=10, prealigned=False, clean=True, align=True):
    """Align a whole directory of .cha files

    Attributes:
        in_directory (string): the directory containing .cha and .wav/.mp3 file
        out_directory (string): the directory for the output files
        data_directory (string): the subdirectory (rel. to out_directory) which the misc.
                                 outputs go
        [model (str)]: the model to use
        [dictionary (str)]: dictionary to use
        [beam (int)]: beam width for initial MFA alignment
        [prealigned (bool)]: whether to start with preexisting alignments from the originial CHA files
        [clean (bool)]: whether to clean up, used for debugging
        [align (bool)]: whether to actually align, used for debugging

    Returns:
        none
    """

    # Define the data_dir
    DATA_DIR = os.path.join(out_directory, data_directory)

    # Make the data directory if needed
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    ### PREPATORY OPS ###
    # convert all mp3s to wavs
    wavs = globase(in_directory, "*.wav")
    # if there are no wavs, convert
    if len(wavs) == 0:
        mp32wav(in_directory)
        mp42wav(in_directory)

    # Generate elan elan elan elan
    chat2elan(in_directory)

    # generate utterance and word-level alignments
    elans = globase(in_directory, "*.eaf")

    if prealigned:
        # convert all chats to TextGrids
        chat2praat(in_directory)
    else:
        # convert all chats to transcripts
        chat2transcript(in_directory)

    # NOTE FOR FUTURE EDITORS
    # TextGrid != textGrid. P2FA and MFA generate different results
    # in terms of capitalization.

    # if we are to align
    if align:
        # Align the files
        align_directory_mfa(in_directory, DATA_DIR, beam=beam, model=model, dictionary=dictionary)

    # find textgrid files
    alignments = globase(DATA_DIR, "*.TextGrid")

    # zip the results and dump into new eafs
    print("Done with MFA! Generating final word-level alignments and bullets...")
    for alignment in tqdm(sorted(alignments)):
        # Find the relative elan file
        elan = repath_file(alignment, in_directory).replace("TextGrid", "eaf").replace("textGrid", "eaf")
        # Align the alignment results
        # MFA TextGrids are long form
        aligned_result = transcript_word_alignment(elan, alignment, alignment_form="long")

        # Calculate the path to the old and new eaf
        old_eaf_path = os.path.join(in_directory,
                                    pathlib.Path(elan).name)
        new_eaf_path = os.path.join(out_directory,
                                    pathlib.Path(elan).name)
        # Dump the aligned result into the new eaf
        eafinject(old_eaf_path, new_eaf_path, aligned_result)
    # convert the aligned eafs back into chat
    elan2chat(out_directory)

    ### CLEANUP OPS ###

    if clean:
        cleanup(in_directory, out_directory, data_directory)

