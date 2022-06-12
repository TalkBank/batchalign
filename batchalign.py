# batchalign.py
# batch alignment tool for chat files and transcripts
#
## INSTALLING CLAN ##
# a full UnixCLAN suite of binaries is placed in ./opt/clan
# For instance, the file ./opt/clan/praat2chat should exist
# and should be executable.
#
## INSTALLING PENN ALIGNER ##
# an htk installation should be present on the system.
# For instance, HVite should be executable. Furthermore
# a full python3 version of p2fa should be placed in ./opt/p2fa
# for instance, ./opt/p2fa/align.py should exist 
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
from typing import ContextManager

# XML facilities
import xml.etree.ElementTree as ET

# Also, include regex
import re

# Import a progress bar
from tqdm import tqdm

# Oneliner of directory-based glob
globase = lambda path, statement: glob.glob(os.path.join(path, statement))

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=os.path.join(CURRENT_PATH, "./opt/clan")
P2FA_PATH=os.path.join(CURRENT_PATH, "./opt/p2fa")

# import p2fa
from opt.p2fa.align import align

# chat2praat a whole path
def chat2praat(directory):
    """Convert a folder of CLAN .cha files to corresponding textGrid files

    Attributes:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # praat2chatit!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2praat')} +e.wav {' '.join(files)} >/dev/null 2>&1"
    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.textGrid"):
        os.rename(f, f.replace(".c2praat", ""))

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

def eaf2transcript(file_path):
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
            # we will now perform some replacements
            # note that the text here is only to help
            # the aligner, because the text is not 
            # used when we are coping time back
            # Remove any disfluency marks
            transcript = re.sub(r"<(.*?)> *?\[.*?\]", r"\1", transcript)
            # Remove any other additions
            transcript = re.sub(r"\[.*?\]",r"", transcript)
            # Remove any additional annotation marks
            transcript = re.sub(r"⌊.*?⌋",r"", transcript)
            transcript = re.sub(r"⌈.*?⌉",r"", transcript)
            transcript = re.sub(r"&=[\w:]*",r"", transcript)
            transcript = re.sub(r"xxx",r"", transcript)
            transcript = re.sub(r"yyy",r"", transcript)
            transcript = re.sub(r"\(.*?\)",r"", transcript)
            # Remove any interruptive marks
            transcript = transcript.replace("+/.","")
            # Remove any quote marks
            transcript = transcript.replace("+\"/","")
            # Remove any pauses
            transcript = transcript.replace("(.)","")
            # And timeslot ID
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

    # begin by chat2elanning a whole path
    chat2elan(directory)

    # then, finding all the elan files
    elan = globase(directory, "*.eaf")

    # and get transcripts from that
    transcripts = [eaf2transcript(i)["transcript"] for i in elan]

    # finally, get the zipped file titles and trascripts
    # and dump each one to file
    for file_title, transcript in zip(elan, transcripts):
        # open the data file
        with open(file_title.replace("eaf","txt"), "w") as df:
            # write to file
            df.writelines([i+"\n" for i in transcript])

    # delete the EAF files
    for eaf_file in elan:
        os.remove(eaf_file)
    
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


# Align a whole directory
def align_directory(directory):
    """Given a directory of .wav and .txt, align them

    Arguments:
        directory (string): string directory filled with .wav and .txt files with same name

    Returns:
        none
    """

    # find the paired wave files and transcripts
    wavs = globase(directory, "*.wav")
    txts = globase(directory, "*.txt")

    # pair them up
    pairs = zip(sorted(wavs), sorted(txts))

    # and then align them!
    for wav, text in tqdm(list(pairs)):
        # Get output file name
        output_filename = wav.replace("wav", "textGrid")
        # Generate align!
        align(wav, text, output_filename, verbose=1)

# Parse a TextGrid file for word tier
def parse_textgrid(file_path):
    """Parse a TextGrid file for the word tier

    Arguments:
        file_path (string): name of the TextGrid file

    Returns:
        none
    """

# Open the file
with open("../data/13-1174.textGrid", "r") as df:
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

wordlist_alignments[2]


parse_textgrid()

# mp32wav("../data")
# chat2transcript("../data")
# align_directory("../data/")

# align("../data/les385su007.wav", "../data/les385su007.txt", "../data/les385su007.textGrid", wave_start="0.0", wave_end="21.0", verbose=1)
