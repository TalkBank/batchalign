# batchalign.py
# batch alignment tool for chat files and transcripts
#
## INSTALLING CLAN ##
# a full UnixCLAN suite of binaries is placed in ./opt/clan
# For instance, the file ./opt/clan/praat2chat should exist
# and should be executable.
#
## INSTALLING MFA ##
# MFA should be present on the system.
# conda config --add channels conda-forge
# conda install montreal-forced-aligner
# conda install pynini
#
## INSTALLING FFMPEG ##
# the penn aligner only aligns wav files. Therefore, we use
# ffmpeg to convert mp3 to wav
#
# Of course, this can be changed if needed.

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

# silence OMP
os.environ["KMP_WARNINGS"] = "FALSE" 

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)
bullet = lambda start,end: f" {int(round(start*1000))}_{int(round(end*1000))}" # start and end should be float seconds

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=""
ATTRIBS_PATH=os.path.join(CURRENT_PATH, "./attribs.cut")

DISFLULENCY_CODE = re.compile("\[.*?\]")

# import textgrid
from opt.textgrid.textgrid import Interval, TextGrid, IntervalTier

# indent an XML
def indent(elem, level=0):
    """Indent an XML

    Attributes:
        element (ET.ElementTree.root): element tree root
        level (int): which level to start aligning from

    Citation:
    https://stackoverflow.com/a/33956544/5684313

    Returns void
    """

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

# chat2elan a whole path
def elan2chat(directory):
    """Convert a folder of CLAN .eaf files to corresponding CHATs

    files:
        directory (string): the string directory in which .elans are in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.eaf")
    # process each file
    for fl in files:
        # elan2chatit!
        CMD = f"{os.path.join(CLAN_PATH, 'elan2chat +c ')} {fl} >/dev/null 2>&1"
        # run!
        os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.elan.cha"):
        os.rename(f, f.replace(".elan.cha", ".cha"))

# chat2elan a whole path
def chat2elan(directory):
    """Convert a folder of CLAN .cha files to corresponding ELAN XMLs

    Note: this function STRIPS EXISTING TIME CODES (though,
          nondestructively)

    files:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # get the name of cleaned files
    files_cleaned = [i.replace(".cha", ".new.cha") for i in files]

    # then, clean out all bullets
    for in_file, out_file in zip(files, files_cleaned):
        # read the in file
        with open(in_file, "r") as df:
            in_file_content = df.read()

        # perform cleaning and write
        cleaned_content = re.sub("\x15.*?\x15", "", in_file_content)

        # write
        with open(out_file, "w") as df:
            df.write(cleaned_content)
            
    # chat2elan it!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2elan')} +c +e.wav {' '.join(files_cleaned)} >/dev/null 2>&1"

    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # delete intermediary
    for f in globase(directory, "*.new.cha"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.new.c2elan.eaf"):
        os.rename(f, f.replace(".new.c2elan.eaf", ".eaf"))

def elan2transcript(file_path):
    """convert an eaf XML file to tiered transcripts

    Attributes:
        file_path (string): file path of the .eaf file

    Returns:
        a dictionary of shape {"transcript":transcript, "tiers":tiers},
        with two arrays with transcript information.
    """

    # Load the file
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file_path, parser=parser)
    root =  tree.getroot()
    tiers = root[2:]

    # create an array for annotations
    annotations = []

    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # we ignore anything that's a "@S*" tier
        # because those are metadata
        if "@" in tier_id:
            continue

        # For each annotation
        for annotation in tier:
            # Get the text of the transcript
            transcript = annotation[0][0].text
            # and append and sort by the time slot references
            try: 
                timeslot_id = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])
            except ValueError:
                print(file_path)

            # and append the metadata + transcript to the annotations
            annotations.append((timeslot_id, tier_id, transcript))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:x[0])

    # we will seperate the tuples after sorting
    _, tiers, transcript = zip(*annotations)

    return {"transcript":transcript, "tiers":tiers}

# chat2transcript a whole path
def chat2transcript(directory):
    """Generate transcripts for a whole directory

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the cha files
    files = globase(directory, "*.cha")

    # use flo to convert chat files to text
    CMD = f"{os.path.join(CLAN_PATH, 'flo +d +ca +t*')} {' '.join(files)} >/dev/null 2>&1"
    # run!
    os.system(CMD)

    # and rename the files to lab files, which are essentially the same thing
    for f in globase(directory, "*.flo.cex"):
        os.rename(f, f.replace(".flo.cex", ".lab"))

# chat2praat, then clean up tiers, for a whole path
def chat2praat(directory):
    """Convert a whole directory to praat files

    Arguments:
        directory (string) : string directory filled with chat

    Returns:
        none
    """
    # then, finding all the cha files
    files = globase(directory, "*.cha")

    # use flo to convert chat files to text
    CMD = f"{os.path.join(CLAN_PATH, 'chat2praat +e.wav +c -t% -t@')} {' '.join(files)} >/dev/null 2>&1"
    # run!
    os.system(CMD)

    # then, finding all the praat files
    praats = globase(directory, "*.c2praat.textGrid")

    for praat in praats:
        # load the textgrid
       os.rename(praat, praat.replace("c2praat.textGrid", "TextGrid"))

    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)


# optionally convert mp3 to wav files
def mp32wav(directory):
    """Generate wav files from mp3

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    mp3s = globase(directory, "*.mp3")

    # convert each file
    for f in mp3s:
        os.system(f"ffmpeg -i {f} {f.replace('mp3','wav')} -c copy")

# optionally convert mp4 to wav files
def mp42wav(directory):
    """Generate wav files from mp4

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    mp4s = globase(directory, "*.mp4")

    # convert each file
    for f in mp4s:
        os.system(f"ffmpeg -i {f} {f.replace('mp4','wav')} -c copy")

def wavconformation(directory):
    """Reconform wav files

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    wavs = globase(directory, "*.wav")

    # convert each file
    for f in wavs:
        # Conforming the wav
        os.system(f"ffmpeg -i {f} temp.wav")
        # move the original
        os.remove(f)
        # and move the new back
        os.rename("temp.wav", f)

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

    # TODO for non-macOS systems
    # check if the g2p model exists, if not, download them
    if not os.path.exists(expanduser("~/Documents/MFA/pretrained_models/g2p/english_us_arpa.zip")):
        # Get and download the model
        CMD = "mfa model download g2p english_us_arpa"
        os.system(CMD)

    # check if the acoustic model exists, if not, download them
    if not os.path.exists(expanduser("~/Documents/MFA/pretrained_models/acoustic/english_us_arpa.zip")):
        # Get and download the model
        CMD = "mfa model download acoustic english_us_arpa"
        os.system(CMD)

    # define model
    if not model:
        model = "english_us_arpa"

    # define dictionary path
    if not dictionary:
        dictionary = os.path.join(directory, 'dictionary.txt')

    # generate dictionary if needed
    if not os.path.exists(dictionary):
        CMD = f"mfa g2p --clean {model} {directory} {dictionary}"
        os.system(CMD)

    # and finally, align!
    CMD = f"mfa align -j 8 --clean {directory} {dictionary} english_us_arpa {data_dir} --beam {beam} --retry_beam 100"
    os.system(CMD)

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
def transcript_word_alignment(elan, alignments, alignment_form="long"):
    """Align the output of parse_transcript and parse_textgrid_* together

    Arguments:
        elan (string): path of elan files
        alignments (string): path of parse_alignments
        alignment_form (string): long or short (MFA or P2FA textGrid)

    Returns:
        {"alignments": ((start, end)...*num_lines), "terms": [bulleted results: string...*num_utterances], "raw": [(word/pause: (start, end)/None)]}
    """

    transcript = elan2transcript(elan)["transcript"]

    # Get alignment form
    if alignment_form == "long":
        aligned_words, _ = parse_textgrid_long(alignments)
    elif alignment_form == "short":
        aligned_words = parse_textgrid_short(alignments)
    else:
        raise Exception(f"unknown alignment_form {alignment_form}")

    # cleaned transcirpt
    unaligned_words = []
    sentence_starts = []
    sentence_ends = []
    
    # we perform cleaning and tokenization of the transcript
    # to create an unaligned word plate. This is used fro
    # matching against the aligned word

    # index becase we'll be doing a lot of shuffling
    i = 0

    # For each sentence
    for current_sentence in transcript:
        # remove extra delimiters
        current_sentence = current_sentence.replace("+","+ ")
        current_sentence = current_sentence.replace("$","$ ")

        # split results
        splits = current_sentence.split(" ")

        # append boundaries
        sentence_starts.append(i)

        # we generate a cleaned and uncleaned match list
        for word in splits:
            cleaned_word = word.lower().replace("(","").replace(")","")
            cleaned_word = cleaned_word.replace("[","").replace("]","")
            cleaned_word = cleaned_word.replace("<","").replace(">","")
            cleaned_word = cleaned_word.replace("“","").replace("”","")
            cleaned_word = cleaned_word.replace(",","").replace("!","")
            cleaned_word = cleaned_word.replace("?","").replace(".","")
            cleaned_word = cleaned_word.replace("+","").replace("&","")
            cleaned_word = cleaned_word.replace(":","").replace("^","")
            cleaned_word = cleaned_word.replace("$","").replace("\"","")
            cleaned_word = re.sub(r"@.", '', cleaned_word)
            cleaned_word = re.sub(r"↫(.*)↫", r'', cleaned_word)

            # append the cleaned and uncleaned versions of words 
            unaligned_words.append((word, cleaned_word, i))
            i += 1

        # append boundaries
        sentence_ends.append(i)

    # conform boundaries
    sentence_boundaries = list([list(range(i,j)) for i,j in zip(sentence_starts, sentence_ends)])

    # we now perform n-round alignment
    # essentially, for each word in the aligned section, we
    # match it to the easiest canidate in the unaligned words
    # to create the final transcript

    aligned_indicies = []
    backplated_alignments = []
    
    # for each word
    for aligned_word, (start, end) in aligned_words:

        # we will go through the unaligned results to find the earlist
        # available canidate

        # for each word
        for word, cleaned_word, i in unaligned_words:
            # if the i is seen, we skip
            if i in aligned_indicies:
                continue

            # if we can align, do align
            if cleaned_word == aligned_word: 
                backplated_alignments.append((i, word, (start, end)))
                aligned_indicies.append(i)
                break

    
    # find missing elements
    to_reinsert = list(filter(lambda x:x[2] not in aligned_indicies, unaligned_words))
    to_reinsert = [(i[2], i[0], None) for i in to_reinsert]

    # sort and reincorporate backplated alignments
    backplated_alignments = sorted(backplated_alignments+to_reinsert, key=lambda i:i[0])

    # set the begin
    j = 0

    # keep track the timestamp
    last_end = 0

    # check if we need backtracking
    # (i.e. "we corrected an error, backpropegate")
    backtracking = False

    # begin a loop to scan and correct errors
    while j < len(backplated_alignments):
        
        # get the results 
        indx, word, interval = backplated_alignments[j]

        # if no interval, we skip
        if not interval and not backtracking:
            j += 1
            continue
        elif not interval:
            j -= 1 
            continue
        
        # reset backtracking
        backtracking = False

        # if there is an interval, we unpack it and ensure
        # that a few things is the case
        start,end = interval

        # get the first remaining indexable elements
        rem = None
        i = indx+1

        # go through in a while loop until we found
        # the next indexable element
        while not rem and i<len(backplated_alignments):
            rem = backplated_alignments[i][2]
            i += 1

        # if end is after the next starting, set the end
        # to be the next starting
        if rem and end > rem[0]:
            end = rem[0]
            backtracking = True # backprop to correct prev. errors

        # if end is smaller than start, conform start to be
        # a bit before end
        if start > end:
            start = max(end, 0.0001)-0.0001
            backtracking = True # backprop to correct prev. errors

        # store the last end, if not backtracking
        if not backtracking:
            last_end = end

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
        sentence = sentence.replace(" >",">")
        sentence = sentence.replace("< ","<")
        sentence = sentence.replace("$ ","$")
        sentence = sentence.replace("& ","&")
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

def eafalign(file_path, alignments, output_path):
    """get an unaligned eaf file to be aligned

    Attributes:
        file_path (string): file path of the .eaf file
        alignments (list or dict): output of transcript word alignment
                                   long or short form will generate diff. results
        output_path (string): output path of the aligned .eaf file

    Returns:
        None
    """

    # Load the file
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file_path, parser=parser)
    root =  tree.getroot()
    tiers = root[2:]

    # create an array for annotations
    annotations = []

    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # we ignore anything that's a "@S*" tier
        # because those are metadata
        if "@" in tier_id:
            continue

        # For each annotation
        for annotation in tier:

            # Parse timeslot ID
            try: 
                timeslot_id_1 = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])
                timeslot_id_2 = int(annotation[0].attrib.get("TIME_SLOT_REF2", "0")[2:])
            except ValueError:
                print(file_path)

            # and append the metadata + transcript to the annotations
            annotations.append(((timeslot_id_1,timeslot_id_2),
                                tier_id,
                                annotation[0].attrib.get("ANNOTATION_ID", "0")))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:int(x[-1][1:]))

    # if we are doing long-form alignment
    if type(alignments) == dict:
        # create a lookup dict 
        terms_flattened = list(zip([i[-1] for i in annotations], alignments["terms"]))
        terms_dict = dict(terms_flattened)

        # set alignment back to what the rest of the function would expect
        alignments = alignments["alignments"]

        # Create the xword annotation ID index
        id_indx = 0

        # replace content with the bulleted version
        # For each tier 
        for tier in tiers:
            # get the name of the tier
            tier_id = tier.attrib.get("TIER_ID","")

            # create new xword tier
            xwor_tier = ET.SubElement(root, "TIER")
            xwor_tier.set("TIER_ID", f"wor@{tier_id}")
            xwor_tier.set("PARTICIPANT", tier_id)
            xwor_tier.set("LINGUISTIC_TYPE_REF", "dependency")
            xwor_tier.set("DEFAULT_LOCALE", "us")
            xwor_tier.set("PARENT_REF", tier_id)

            # we delete all previous xwor/wor tiers
            if "wor" in tier_id or "xwor" in tier_id:
                root.remove(tier)
                continue

            # we ignore anything that's a "@S*" tier
            # because those are metadata
            if "@" in tier_id:
                continue

            # For each annotation
            for annotation in tier:
                # get annotation
                annotation = annotation[0]
                # get ID
                annot_id = annotation.attrib.get("ANNOTATION_ID", "0")

                # append annotation line
                # create two element
                xwor_annot = ET.SubElement(xwor_tier, 'ANNOTATION')
                xwor_annot_cont = ET.SubElement(xwor_annot, 'REF_ANNOTATION')

                # adding annotation metadata
                xwor_annot_cont.set("ANNOTATION_ID", f"xw{id_indx}")
                xwor_annot_cont.set("ANNOTATION_REF", annot_id)

                # and add content
                xwor_word_cont = ET.SubElement(xwor_annot_cont, "ANNOTATION_VALUE")

                # with the bulleted content
                xwor_word_cont.text = terms_dict.get(annot_id)

                # update index
                id_indx += 1

    # Remove the old time slot IDs
    root[1].clear()

    # For each of the resulting annotations, dump the time values
    # Remember that time values dumped in milliseconds so we
    # multiply the result by 1000 and round to int
    for annotation, alignment in zip(annotations, alignments):
        # Create the beginning time slot
        element_start = ET.Element("TIME_SLOT")
        # Set the time slot ID to the correct beginning
        element_start.set("TIME_SLOT_ID", f"ts{annotation[0][0]}")

        # Create the beginning time slot
        element_end = ET.Element("TIME_SLOT")
        # Set the time slot ID to the correct beginning
        element_end.set("TIME_SLOT_ID", f"ts{annotation[0][1]}")

        # if alignment is not None, set time value
        if alignment:
            # Set the time slot ID to the correct end
            element_start.set("TIME_VALUE", f"{int(alignment[0]*1000)}")
            # Set the time slot ID to the correct end
            element_end.set("TIME_VALUE", f"{int(alignment[1]*1000)}")

        # Appending the element
        root[1].append(element_start)
        root[1].append(element_end)

    # Indent the tree
    indent(root)
    # And write tit to file
    tree.write(output_path, encoding="unicode", xml_declaration=True)

def retokenize_directory(in_directory, model_path):
    """Retokenize the directory, or read Rev.ai JSON files and generate .cha

    Attributes:
        in_directory (str): input directory containing files
        model_path (str): path to a BertTokenizer and BertModelForTokenClassification
                          trained on the segmentation task.

    Returns:
        None, used for .cha file generation side effects.
    """

    # we import here for backwards dependency capatability
    from utterance import retokenize
    from utokengine import UtteranceEngine

    # find all the JSON files
    files = globase(in_directory, "*.json")
    # if we have no JSON files, we assume that the input
    # chat files are .cha (Andrew edition)
    if len(files) == 0:
        # we will scan for .cha files
        files = globase(in_directory, "*.cha")
        # move them to the .orig directory
        for f in files:
            # move to .old
            os.rename(f,f.replace("cha",".orig.cha"))
        # we will scan for .cha files again, with new dir
        files = globase(in_directory, "*.cha")
    # seed an utterance engine to use
    E = UtteranceEngine(model_path)
    # we will then perform the retokenization
    for f in files:
        # retokenize the file!
        retokenize(f, f.replace(pathlib.Path(f).suffix, ".cha"), E)
    
def cleanup(in_directory, out_directory, data_directory="data"):
    """Clean up alignment results so that workspace is clear

    Attributes:
        in_directory (string): the input directory containing files
        out_directory (string): the output directory containing possible output files
        data_directory (string): a subdirectory which the misc. outputs go

    Returns:
        none
    """

    # Define the data_dir
    DATA_DIR = os.path.join(out_directory, data_directory)

    # move all the lab files 
    tgfiles = globase(in_directory, "*.textGrid")
    # Rename each one
    for f in tgfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the lab files 
    tgfiles = globase(in_directory, "*.TextGrid")
    # Rename each one
    for f in tgfiles:
        os.rename(f, repath_file(f.replace("TextGrid", "orig.textGrid"), DATA_DIR)) 

    # move all the lab files 
    labfiles = globase(in_directory, "*.lab")
    # Rename each one
    for f in labfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the wav files 
    wavfiles = globase(in_directory, "*.orig.wav")
    # Rename each one
    for f in wavfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the rest of wav files 
    mp3files = globase(in_directory, "*.mp3")
    # Rename each one
    for f in mp3files:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the rest of mp4 files 
    mp4files = globase(in_directory, "*.mp4")
    # Rename each one
    for f in mp4files:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the orig.cha files from repathing
    chafiles = globase(in_directory, "*.orig.cha")
    # Rename each one
    for f in chafiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # clean up the elans
    elanfiles = globase(out_directory, "*.eaf")
    # Rename each one
    for f in elanfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # Clean up the dictionary, if exists
    dict_path = os.path.join(in_directory, "dictionary.txt")
    # Move it to the data dir too
    if os.path.exists(dict_path):
        os.rename(dict_path, repath_file(dict_path, DATA_DIR))

    # Cleaning up
    # Removing all the eaf files generated
    for eaf_file in globase(in_directory, "*.eaf"):
        os.remove(eaf_file)
    for eaf_file in globase(out_directory, "*.eaf"):
        os.remove(eaf_file)

    # Removing all the transcript files generated
    for eaf_file in globase(in_directory, "*.txt"):
        os.remove(eaf_file)


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

        # Perform disfluency calculation TODO
        # disfluency_calculation(aligned_result["raw"], [random.choice(["A","B"]) for i in range (len(aligned_result["raw"]))])

        # Calculate the path to the old and new eaf
        old_eaf_path = os.path.join(in_directory,
                                    pathlib.Path(elan).name)
        new_eaf_path = os.path.join(out_directory,
                                    pathlib.Path(elan).name)
        # Dump the aligned result into the new eaf
        eafalign(old_eaf_path, aligned_result, new_eaf_path)
    # convert the aligned eafs back into chat
    elan2chat(out_directory)

    ### CLEANUP OPS ###

    if clean:
        cleanup(in_directory, out_directory, data_directory)

# manloop to take input
parser = argparse.ArgumentParser(description="batch align .cha to audio in a directory with MFA/P2FA")
parser.add_argument("in_dir", type=str, help='input directory containing .cha and .mp3/.wav files')
parser.add_argument("out_dir", type=str, help='output directory to store aligned .cha files')
parser.add_argument("--prealigned", default=False, action='store_true', help='input .cha has utterance-level alignments')
parser.add_argument("--data_dir", type=str, default="data", help='subdirectory of out_dir to use as data dir')
parser.add_argument("--beam", type=int, default=30, help='beam width for MFA, ignored for P2FA')
parser.add_argument("--skipalign", default=False, action='store_true', help='don\'t align, just call CHAT ops')
parser.add_argument("--skipclean", default=False, action='store_true', help='don\'t clean')
parser.add_argument("--dictionary", type=str, help='path to custom dictionary')
parser.add_argument("--model", type=str, help='path to custom model')
parser.add_argument("--retokenize", type=str, help='retokenize input with model')
parser.add_argument("--clean", default=False, action='store_true', help='don\'t align, just call cleanup')

if __name__=="__main__":
    args = parser.parse_args()

    if args.clean:
        cleanup(args.in_dir, args.out_dir, args.data_dir)
    elif args.retokenize:
        if not args.prealigned:
            print("--prealigned flag not provided. as source came from ASR, prealigned mode will be enabled.")
        print("Performing retokenization!")
        retokenize_directory(args.in_dir, args.retokenize)
        print("Done. Handing off to MFA.")
        do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=True, beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.model)
    else: 
        do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=args.prealigned, beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.model)

# ((word, (start_time, end_time))... x number_words)
