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

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=""
P2FA_PATH=os.path.join(CURRENT_PATH, "./opt/p2fa_py3/p2fa")
ATTRIBS_PATH=os.path.join(CURRENT_PATH, "./attribs.cut")

# import p2fa
from opt.p2fa_py3.p2fa.align import align

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
def parse_textgrid(file_path):
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
    lines_split = [[j.upper() for j in re.compile("[ .,?!-]+").split(i)[:-1]] for i in lines]

    return lines_split[:-1]

# Align the alignments!
def transcript_word_alignment(transcript, alignments):
    """Align the output of parse_transcript and parse_textgrid together

    Arguments:
        transcript (string): path of parse_transcript wordlist
        alignments (string): path of parse_alignments

    Returns:
        ((start, end)...*num_lines
    """

    transcript = parse_transcript(transcript)
    wordlist_alignments = parse_textgrid(alignments)

    # Get the top word to be aligned
    current_word = wordlist_alignments.pop(0)

    # Create a list of start and end results
    alignments = []

    # For each sentence
    for current_sentence in transcript:
        # Set start and end for the current interval
        start = current_word[1][0]
        end = current_word[1][1] # create template ending in case the end doesn't exist

        # for the current word in the current sentence
        # check if it is the current word. If it is, move
        # on and update end interval. If not, ignore the wrod
        for word in current_sentence:
            # If we got the current word, move on to the next
            if word == current_word[0]:
                try: 
                    current_word = wordlist_alignments.pop(0)
                except IndexError:
                    break # we have reached the end

        # The end should be the beginning of the "next" word
        end = current_word[1][0]

        # Append the start and end intervals we aligned
        alignments.append((start,end))

    # Return the fimal alignments
    return alignments

def eafalign(file_path, alignments, output_path):
    """get an unaligned eaf file to be aligned

    Attributes:
        file_path (string): file path of the .eaf file
        alignments (list): output of transcript word alignment
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
            annotations.append(((timeslot_id_1,timeslot_id_2), tier_id))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:x[0])

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

def do_align(in_directory, out_directory, data_directory="data", method="mfa"):
    """Align a whole directory of .cha files

    Attributes:
        in_directory (string): the directory containing .cha and .wav/.mp3 file
        out_directory (string): the directory for the output files
        data_directory (string): the subdirectory (rel. to out_directory) which the misc.
                                 outputs go

        method (string): your choice of 'mfa' or 'p2fa' for alignment

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

    # P2FA/Montreal time
    if method.lower()=="mfa":
        # Align the files
        align_directory_mfa(in_directory, DATA_DIR)
        # Convert to chat files
        mfa2chat(in_directory, out_directory, DATA_DIR)
    elif method.lower()=="p2fa":
        # Generate elan elan elan elan
        chat2elan(in_directory)

        # Align files
        align_directory_p2fa(in_directory)

        # generate utterance-level alignments
        transcripts = globase(in_directory, "*.lab")
        alignments = globase(in_directory, "*.textGrid")


        # zip the results and dump into neaw eafs
        for transcript, alignment in zip(sorted(transcripts), sorted(alignments)):
            # Align the alignment results
            aligned_result = transcript_word_alignment(transcript, alignment)
            # Calculate the path to the old and new eaf
            old_eaf_path = os.path.join(in_directory,
                                        pathlib.Path(transcript).name.replace("lab", "eaf"))
            new_eaf_path = os.path.join(out_directory,
                                        pathlib.Path(transcript).name.replace("lab", "eaf"))
            # Dump the aligned result into the new eaf
            eafalign(old_eaf_path, aligned_result, new_eaf_path)
        
        # convert the aligned eafs back into chat
        elan2chat(out_directory)

    else:
        raise Exception(f'Unknown forced alignment method {method}.')

    ### CLEANUP OPS ###

    # And, move all the files that we generated there
    # if we generated the .wavs, move the wavs
    mp3files = globase(in_directory, "*.mp3")
    if len(mp3files) > 0:
        # Rename each of the generated wavs
        for f in mp3files:
            os.rename(f.replace("mp3", "wav"), repath_file(f.replace("mp3", "wav"), DATA_DIR)) 

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
