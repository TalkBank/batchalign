# batchalign.py
# batch alignment tool for chat files and transcripts
#
## INSTALLING CLAN ##
# a full UnixCLAN suite of binaries is placed in ./opt/clan
# For instance, the file ./opt/clan/praat2chat should exist
# and should be executable.
#
## For P2FA: INSTALLING HTK  ##
# an htk installation should be present on the system.
# For instance, HVite should be executable. 
#
## For MFA: INSTALLING MFA ##
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
 
# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)
bullet = lambda start,end: f" {int(round(start*1000))}_{int(round(end*1000))} " # start and end should be float seconds

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=""
P2FA_PATH=os.path.join(CURRENT_PATH, "./opt/p2fa_py3/p2fa")
ATTRIBS_PATH=os.path.join(CURRENT_PATH, "./attribs.cut")

# import p2fa
from opt.p2fa_py3.p2fa.align import align

# import textgrid
from opt.textgrid.textgrid import TextGrid

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
    # praat2chatit!
    CMD = f"{os.path.join(CLAN_PATH, 'elan2chat')} {' '.join(files)} >/dev/null 2>&1"
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

    files:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # praat2chatit!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2elan')} +e.wav {' '.join(files)} >/dev/null 2>&1"
    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.eaf"):
        os.rename(f, f.replace(".c2elan", ""))

def elan2transcript(file_path):
    """convert an eaf XML file to tiered transcripts

    Attributes:
        file_path (string): file path of the .eaf file

    Returns:
        a dictionary of shape {"transcript":transcript, "tiers":tiers},
        with two arrays with transcript information.
    """

    # Load the file
    tree = ET.parse(file_path)
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
    CMD = f"{os.path.join(CLAN_PATH, 'flo +d +cr +t*')} {' '.join(files)} >/dev/null 2>&1"
    # run!
    os.system(CMD)

    # and rename the files to lab files, which are essentially the same thing
    for f in globase(directory, "*.flo.cex"):
        os.rename(f, f.replace(".flo.cex", ".lab"))
   
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

# Align a whole directory
def align_directory_p2fa(directory):
    """Given a directory of .wav and .lab, align them

    Arguments:
        directory (string): string directory filled with .wav and .txt files with same name

    Returns:
        none
    """

    # find the paired wave files and transcripts
    wavs = globase(directory, "*.wav")
    txts = globase(directory, "*.lab")

    # pair them up
    pairs = zip(sorted(wavs), sorted(txts))

    # and then align them!
    for wav, text in pairs:
        print(f"aligning {wav}")
        # Get output file name
        output_filename = wav.replace("wav", "textGrid")
        # Generate align!
        align(wav, text, output_filename, verbose=1)

def align_directory_mfa(directory, data_dir):
    """Given a directory of .wav and .lab, align them

    Arguments:
        directory (string): string directory filled with .wav and .lab files with same name
        data_dir (string): output directory for textgrids

    Returns:
        none
    """

    # TODO for non-macOS systems
    # check if the g2p model exists, if not, download them
    if not os.path.exists("~/Documents/MFA/extracted_models/g2p/english_us_arpa"):
        # Get and download the model
        CMD = "mfa model download g2p english_us_arpa"
        os.system(CMD)

    # check if the acoustic model exists, if not, download them
    if not os.path.exists("~/Documents/MFA/extracted_models/acoustic/english_us_arpa"):
        # Get and download the model
        CMD = "mfa model download acoustic english_us_arpa"
        os.system(CMD)

    # define dictionary path
    dictionary = os.path.join(directory, 'dictionary.txt')

    # generate dictionary if needed
    if not os.path.exists(dictionary):
        CMD = f"mfa g2p --clean english_us_arpa {directory} {dictionary}"
        os.system(CMD)

    # and finally, align!
    CMD = f"mfa align --clean {directory} {dictionary} english_us_arpa {data_dir}"
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
    word = text_grid[0]
    pho = text_grid[1]

    # Convert pho and word tiers
    word_tiers = [(i.mark, (i.minTime, i.maxTime)) for i in word]
    phone_tiers = [(i.mark, (i.minTime, i.maxTime)) for i in pho]

    # Skip all blanks
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

# Parse a generated transcript
def parse_transcript(file_path):
    """Parse a transcript file

    Arguments:
        file_path (string): name of the transcript file

    Returns:
        A list of [[word... * words]... * utterances]
    """

    # Open the transcript file
    with open(file_path, "r") as df:
        data = df.read()
    # Split the lines of the data 
    lines = data.split("\n")
    # Split each line (replacing all punctuations with spaces and split
    # by spaces
    lines_split = [[j for j in re.compile("[ .,?!-]+").split(i)[:-1]] for i in lines]

    return lines_split[:-1]

# Align the alignments!
def transcript_word_alignment(elan, alignments, alignment_form="long"):
    """Align the output of parse_transcript and parse_textgrid_* together

    Arguments:
        elan (string): path of elan files
        alignments (string): path of parse_alignments
        alignment_form (string): long or short (MFA or P2FA textGrid)

    Returns:
        {"alignments": ((start, end)...*num_lines), "terms": [bulleted results: string...*num_utterances]}
    """

    transcript = elan2transcript(elan)["transcript"]

    # Get alignment form
    if alignment_form == "long":
        wordlist_alignments, _ = parse_textgrid_long(alignments)
    elif alignment_form == "short":
        wordlist_alignments = parse_textgrid_short(alignments)
    else:
        raise Exception(f"unknown alignment_form {alignment_form}")
    

    # Get the top word to be aligned
    current_word = wordlist_alignments.pop(0)

    # Create a list of start and end results
    alignments = []
    # Create a list of results
    results = []

    # For each sentence
    for current_sentence in transcript:
        # Set start and end for the current interval
        start = current_word[1][0]
        end = current_word[1][1] # create template ending in case the end doesn't exist

        # create a running buffer
        buff = []

        # for the current word in the current sentence
        # check if it is the current word. If it is, move
        # on and update end interval. If not, ignore the wrod
        for word in current_sentence.split(" "):
            # clean the word
            cleaned_word = word.lower().replace("(","").replace(")","")
            cleaned_word = cleaned_word.replace("[","").replace("]","")
            cleaned_word = re.sub(r"@.", '', cleaned_word)
            # cleaned_word = re.sub(r"[^\w\s\-]*", '', cleaned_word)
            # If we got the current word, move on to the next
            # you will notice we replace the parenthese because those are in-text
            # disfluency adjustments
            if cleaned_word == current_word[0].lower():
                # append current word
                buff.append((word.lower(), (current_word[1][0], current_word[1][1])))
                try: 
                    current_word = wordlist_alignments.pop(0)
                except IndexError:
                    break # we have reached the end

            # TODO HACKY!!
            # I am carveout. I'm is parsed differently in
            # MFA for no good reason
            elif (word.lower() == "i'm" and current_word[0].lower() == "i" and wordlist_alignments[0][0] =="'m"):
                # append current word up until the end of the 'm
                buff.append(("I'm", (current_word[1][0], wordlist_alignments[0][1][1])))
                # Ignore the am
                wordlist_alignments.pop(0)
                # and append as usual
                try: 
                    current_word = wordlist_alignments.pop(0)
                except IndexError:
                    break # we have reached the end
            else:
                # just append a non-bulleted word 
                buff.append((word, None))

        # The end should be the beginning of the "next" word
        end = current_word[1][0]

        # Append the start and end intervals we aligned
        alignments.append((start,end))
        results.append(buff.copy())

    bulleted_results = []
    # Convert bulleted results
    for sentence in results:
        # bullet the sentence
        sentence_bulleted = []
        # for each term
        for i in sentence:
            # if alignable, append a bullet
            if i[1]:
                sentence_bulleted.append(i[0].strip()+bullet(i[1][0], i[1][1]))
            else:
                sentence_bulleted.append(i[0])
        # concat and append to bulleted results
        bulleted_results.append(" ".join(sentence_bulleted).strip())

    # Return the fimal alignments
    return {"alignments": alignments, "terms": bulleted_results}

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
    tree = ET.parse(file_path)
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
            annotations.append(((timeslot_id_1,timeslot_id_2), tier_id, annotation[0].attrib.get("ANNOTATION_ID", "0")))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:int(x[-1][1:]))

    # if we are doing long-form alignment
    if type(alignments) == dict:
        # create a lookup dict 
        terms_flattened = list(zip([i[-1] for i in annotations], alignments["terms"]))
        terms_dict = dict(terms_flattened)

        # set alignment back to what the rest of the function would expect
        alignments = alignments["alignments"]

        # replace content with the bulleted version
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
                # get annotation
                annotation = annotation[0]
                # get ID
                annot_id = annotation.attrib.get("ANNOTATION_ID", "0")

                # set annotation text
                annotation[0].text = terms_dict.get(annot_id)

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
        # Set the time slot ID to the correct end
        element_start.set("TIME_VALUE", f"{int(alignment[0]*1000)}")

        # Create the beginning time slot
        element_end = ET.Element("TIME_SLOT")
        # Set the time slot ID to the correct beginning
        element_end.set("TIME_SLOT_ID", f"ts{annotation[0][1]}")
        # Set the time slot ID to the correct end
        element_end.set("TIME_VALUE", f"{int(alignment[1]*1000)}")

        # Appending the element
        root[1].append(element_start)
        root[1].append(element_end)

    # And write tit to file
    tree.write(output_path)

def mfa2chat(in_dir, out_dir, data_dir):
    """Align mfa to chat files

    Attributes:
        in_dir (string): in directory 
        out_dir (string): out directory
        data_dir (string): in directory of data

    """

    # Move all the audio files to the data_dir
    wav_files = globase(in_dir, "*.wav")
    for wav_file in wav_files:
        os.rename(wav_file, repath_file(wav_file, data_dir))
    
    # Move all the cha file to the data dir
    cha_files = globase(in_dir, "*.cha")
    for cha_file in cha_files:
        os.rename(cha_file, repath_file(cha_file, data_dir))

    # Move all the lab file to the data dir
    lab_files = globase(in_dir, "*.lab")
    for lab_file in lab_files:
        os.rename(lab_file, repath_file(lab_file, data_dir))

    # mfa2chat the results
    tg_files = globase(data_dir, "*.TextGrid")
    # For each file
    for tg_file in tg_files:
        # mfa2chat command and run!
        CMD=f"mfa2chat +opcl +d{ATTRIBS_PATH} {tg_file}"
        os.system(CMD)

    # Move all the .mfa.cha to out directory as .cha
    mfa_files = globase(data_dir, "*.mfa.cha")
    for mfa_file in mfa_files:
        os.rename(mfa_file, repath_file(mfa_file.replace(".mfa.cha", ".cha"), out_dir))

    # Move all the cha and wav file back
    # Move all the audio files to the in_dir
    for wav_file in wav_files:
        os.rename(repath_file(wav_file, data_dir), wav_file)
    
    # Move all the cha file to the data dir
    for cha_file in cha_files:
        os.rename(repath_file(cha_file, data_dir), cha_file)

def do_align(in_directory, out_directory, data_directory="data", method="mfa", cleanup=True):
    """Align a whole directory of .cha files

    Attributes:
        in_directory (string): the directory containing .cha and .wav/.mp3 file
        out_directory (string): the directory for the output files
        data_directory (string): the subdirectory (rel. to out_directory) which the misc.
                                 outputs go
        method (string): your choice of 'mfa' or 'p2fa' for alignment
        cleanup (bool): whether to clean up, used for debugging

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

    # convert all chats to transcripts
    chat2transcript(in_directory)

    # Generate elan elan elan elan
    chat2elan(in_directory)

    # generate utterance and word-level alignments
    elans = globase(in_directory, "*.eaf")

    # NOTE FOR FUTURE EDITORS
    # TextGrid != textGrid. P2FA and MFA generate different results
    # in terms of capitalization.

    if method.lower()=="mfa":
        # Align the files
        align_directory_mfa(in_directory, DATA_DIR)

        # find textgrid files
        alignments = globase(DATA_DIR, "*.TextGrid")
    elif method.lower()=="p2fa":
        # conforms wavs
        wavconformation(in_directory)
        # Align files
        align_directory_p2fa(in_directory)

        # find textgrid files
        alignments = globase(in_directory, "*.textGrid")
    else:
        raise Exception(f'Unknown forced alignment method {method}.')

    # zip the results and dump into neaw eafs
    for elan, alignment in zip(sorted(elans), sorted(alignments)):
        # Align the alignment results
        if method.lower()=="mfa":
            # MFA TextGrids are long form
            aligned_result = transcript_word_alignment(elan, alignment, alignment_form="long")
        elif method.lower()=="p2fa":
            # P2FA TextGrids are short form
            aligned_result = transcript_word_alignment(elan, alignment, alignment_form="short")
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

    if cleanup:
        # move all the lab files 
        tgfiles = globase(in_directory, "*.textGrid")
        # Rename each one
        for f in tgfiles:
            os.rename(f, repath_file(f, DATA_DIR)) 

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

# manloop to take input
parser = argparse.ArgumentParser(description="batch align .cha to audio in a directory with MFA/P2FA")
parser.add_argument("in_dir", type=str, help='input directory containing .cha and .mp3/.wav files')
parser.add_argument("out_dir", type=str, help='output directory to store aligned .cha files')
parser.add_argument("--data_dir", type=str, default="data", help='subdirectory of out_dir to use as data dir')
parser.add_argument("--method", type=str, default="mfa", help='method to use to perform alignment')

if __name__=="__main__":
    args = parser.parse_args()
    do_align(args.in_dir, args.out_dir, args.data_dir, args.method)

# ((word, (start_time, end_time))... x number_words)
