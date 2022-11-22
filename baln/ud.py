# system utils
import glob, os, re

# pathing tools
from pathlib import Path

# UD tools
import stanza
from stanza.pipeline.core import CONSTITUENCY
from stanza import DownloadMethod

# tqdm
from tqdm import tqdm

# out utiltiies
from .utils import *
from .eaf import *

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)

def parse_sentence(sentence):
    """Parses Stanza sentence into %mor and %gra strings

    Arguments:
        sentence: the stanza sentence object

    Returns:
        (str, str): (mor_string, gra_string)---strings matching
                    the output to be returned to %mor and %gra
    """

    # parse analysis results
    mor = []
    gra = []

    for indx, word in enumerate(sentence.words):
        # parse the UNIVERSAL parts of speech
        mor.append(f"{word.upos.lower()}|{word.lemma}")
        # +1 because we are 1-indexed
        # and .head is also 1-indexed already
        gra.append(f"{indx+1}|{word.head}|{word.deprel.upper()}")

    mor_str = (" ".join(mor)).strip()
    gra_str = (" ".join(gra)).strip()

    return (mor_str, gra_str)

def morphanalyze(in_directory, out_directory, data_directory="data", language="en", clean=True):
    """Batch morphosyntactic analysis tools using Stanza

    Arguments:
        in_directory (string): the directory containing .cha and .wav/.mp3 file
        out_directory (string): the directory for the output files
        [language (string)]: what language are we analyzing?
        [data_directory (string)]: the subdirectory (rel. to out_directory) which the misc.
                                   outputs go
        [clean (bool)]: whether to clean up, used for debugging

    Returns:
        none
    """

    # Define the data_dir
    DATA_DIR = os.path.join(out_directory, data_directory)

    # Make the data directory if needed
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    print("Starting Stanza...")

    nlp = stanza.Pipeline(language,
                          processors='tokenize,pos,lemma,depparse',
                          download_method=DownloadMethod.REUSE_RESOURCES)

    # create label and elan files
    chat2transcript(in_directory)
    chat2elan(in_directory)

    # process each file
    print("Performing analysis...")
    for f in globase(in_directory, "*.cha"):
        print(f"Morphosyntactic tagging {Path(f).stem}.cha...")

        # get file names
        label_file = f.replace("cha", "lab")
        elan_file = f.replace("cha", "eaf")
        elan_target = repath_file(elan_file, out_directory)

        # open label file
        with open(label_file, 'r') as df:
            # so, for some reason, .lab outputs some lines
            # truncated with a \t in the begining. so we
            # replace out the \n\t with just a space
            data = df.read()
            labels = data.replace('\n\t',' ').strip().split('\n')

        # perform analysis
        sentences = []
        for line in tqdm(labels):
            sentences.append(parse_sentence(nlp(line).sentences[0]))

        # inject into EAF
        # we have no MFA alignments, instead, we are injecting
        # morphological data
        inject_eaf(elan_file, elan_target,
                   alignments=None,
                   morphodata=sentences)

    # convert the prepared eafs back into chat
    elan2chat(out_directory)

    # cleanup!
    if clean:
        cleanup(in_directory, out_directory, data_directory)
        
       
