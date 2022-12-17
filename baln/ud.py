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
# one liner to parse features
parse_feats = lambda word: {i.split("=")[0]: i.split("=")[1] for i in word.feats.split("|")}

# the following is a list of feature-extracting handlers
# it is used to extract features from specific parts of
# speech. 

def handler(word):
    """The generic handler"""

    # if the lemma is ", return the word
    # not sure what errors are coming along?
    target = word.lemma
    if target == '"':
        target = word.text

    return f"{word.upos.lower()}|{target}"

# POS specific handler
def handler__AUX(word):
    # get the features
    feats = parse_feats(word)
    # featflag
    flag = str(feats.get("Person", 1))+str(feats.get("Number", "S")[0])
    # if the tense is not present, talk about it as past
    if feats.get("Tense", "Pres") != "Pres":
        flag += "&"+feats.get("Tense", "Pres").upper()
    return handler(word)+"&"+flag

# POS specific handler
def handler__VERB(word):
    # get the features
    feats = parse_feats(word)
    if feats.get("Tense") == "Past" and feats.get("VerbForm") == "Part":
        return handler(word)+"&PASTP"
    else:
        return handler(word)

def handler__PUNCT(word):
    if word.lemma==",":
        return "cm|cm"
    elif word.lemma in ['.', '!', '?']:
        return word.lemma
    # all other cases return None
    # to skip

# UPOS: Handler
HANDLERS = {
    "AUX": handler__AUX,
    "PUNCT": handler__PUNCT,
    "VERB": handler__VERB
}

# the follow
def parse_sentence(sentence, delimiter="."):
    """Parses Stanza sentence into %mor and %gra strings

    Arguments:
        sentence: the stanza sentence object

    Returns:
        (str, str): (mor_string, gra_string)---strings matching
                    the output to be returned to %mor and %gra
        [delimiter]: how to end the utterance
    """

    # parse analysis results
    mor = []
    gra = []

    for indx, word in enumerate(sentence.words):
        # append the appropriate mor line
        # by trying all handlers, and defaulting
        # to the default handler
        mor_word = HANDLERS.get(word.upos, handler)(word)
        # some handlers may return None to skip the word
        if mor_word:
            mor.append(mor_word)
        # +1 because we are 1-indexed
        # and .head is also 1-indexed already
        gra.append(f"{indx+1}|{word.head}|{word.deprel.upper()}")

    mor_str = (" ".join(mor)).strip()
    gra_str = (" ".join(gra)).strip()

    # add the endning delimiter
    mor_str = mor_str

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
    chat2transcript(in_directory, True)
    chat2elan(in_directory)

    # process each file
    print("Performing analysis...")
    for f in globase(in_directory, "*.cha"):
        print(f"Tagging {Path(f).stem}.cha...")

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
            # we remove all the subtiers; like %par: etc.
            labels = filter(lambda x:x[0] != '%', labels)
            # we now want to remove the tier name tag, because we don't
            # care about it
            labels = [label.split("\t")[1] for label in labels]

        # perform analysis
        sentences = []
        for line in tqdm(labels):
            # every legal utterance will have an ending delimiter
            # so we split it out
            ending = line.split(" ")[-1]
            line_cut = line[:-len(ending)].strip()

            # if we don't have anything in line cut, just take the original
            # this is compensating for things that are missing ending decimeters
            if line_cut == '':
                line_cut = line
                ending = '.'

            sentences.append(parse_sentence(nlp(line_cut).sentences[0], ending))

        # inject into EAF
        # we have no MFA alignments, instead, we are injecting
        # morphological data
        eafinject(elan_file, elan_target,
                   alignments=None,
                   morphodata=sentences)

    # convert the prepared eafs back into chat
    elan2chat(out_directory)

    # and then find all the chat files, removing bullets from them
    for f in globase(out_directory, "*.cha"):
        strip_bullets(f)

    # cleanup!
    if clean:
        cleanup(in_directory, out_directory, data_directory)
        
       
