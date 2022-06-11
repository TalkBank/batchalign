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

# XML facilities
import xml.etree.ElementTree as ET

# Also, include regex
import re

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
    CMD = f"{os.path.join(CLAN_PATH, 'chat2praat')} +e.wav {' '.join(files)}"
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
    CMD = f"{os.path.join(CLAN_PATH, 'chat2elan')} +e.wav {' '.join(files)}"
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
            # Remove any interruptive marks
            transcript = transcript.replace("+/.","")
            # Remove any quote marks
            transcript = transcript.replace("+\"/","")
            # Remove any pauses
            transcript = transcript.replace("(.)","")
            # And timeslot ID
            timeslot_id = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])

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
