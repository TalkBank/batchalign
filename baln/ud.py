# system utils
import glob, os, re

# pathing tools
from pathlib import Path

# UD tools
import stanza
from stanza.pipeline.core import CONSTITUENCY
from stanza import DownloadMethod
from torch import heaviside

# tqdm
from tqdm import tqdm

# out utiltiies
from .utils import *
from .eaf import *

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)
# one liner to parse features
def parse_feats(word):
    try:
        return {i.split("=")[0]: i.split("=")[1] for i in word.feats.split("|")}
    except AttributeError:
        return {}

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

    # unknown flag
    unknown = False
    
    # if there is a 0 in front, the word is unkown
    # so we mark it as such
    if target[0] == '0':
        target = word.text[1:]
        unknown = True

    # if there is..... dear god, a sequence start <SOS>
    # token in the model output, return the text instead
    # of teh predicted lemma as something has gone very wrong
    if "<SOS>" in target:
        target = word.text

    return f"{'' if not unknown else '0'}{word.upos.lower()}|{target}"

# POS specific handler
def handler__PRON(word):
    # get the features
    feats = parse_feats(word)
    # parse
    return (handler(word)+"-"+
            feats.get("PronType", "Int")+"-"+
            feats.get("Case", "Acc")+"-"+
            feats.get("Number", "S")[0]+str(feats.get("Person", 1)))

def handler__DET(word):
    # get the features
    try:
        feats = parse_feats(word)
    except AttributeError:
        return handler(word)
    # parse
    return (handler(word)+"-"+
            feats.get("Definite", "Def"))

def handler__ADJ(word):
    # get the features
    feats = parse_feats(word)
    # if there is a non-degree
    deg = feats.get("Degree", "Pos")
    return handler(word)+(("-"+deg) if deg != "Pos" else "") 

def handler__NOUN(word):
    # get the features
    feats = parse_feats(word)

    # get gender and numer
    gender_str = "&"+feats.get("Gender", "Com,Neut")
    number_str = "-"+feats.get("Number", "Sing")

    # clear defaults
    if gender_str == "&Com,Neut" or gender_str == "&Com": gender_str=""
    if number_str == "-Sing": number_str=""

    return handler(word)+gender_str+number_str

def handler__PROPN(word):
    # code as noun
    parsed = handler__NOUN(word)
    return parsed.replace("propn", "noun")

def handler__VERB(word):
    # get the features
    feats = parse_feats(word)
    # seed flag
    flag = ""
    # append number and form if needed
    flag += "-"+feats.get("VerbForm", "Inf")
    number = feats.get("Number", "Sing")
    if number != "Sing":
        flag += f"-{number}"
    # append tense
    if feats.get("Tense", "Pres") == "Past":
        flag += "-Past"
    return handler(word)+flag

def handler__actual_PUNCT(word):
    # actual punctuation handler
    if word.lemma==",":
        return "cm|cm"
    elif word.lemma in ['.', '!', '?']:
        return word.lemma
    # all other cases return None
    # to skip

def handler__PUNCT(word):
    # no idea why SYM and PUNCT returns punctuation
    # or sometimes straight up words, but  so it goes
    # either punctuation or inflection words
    if word.lemma in ['.', '!', '?', ',']:
        return handler__actual_PUNCT(word)
    # otherwise, if its a word, return the word
    elif re.match(r"^\w+$", word.text): # we match text here because .text is the ultumate content
                                        # instead of the lemma, which maybe entirely weird
        return handler(word)

# Register handlers
HANDLERS = {
    "PRON": handler__PRON,
    "DET": handler__DET,
    "ADJ": handler__ADJ,
    "NOUN": handler__NOUN,
    "PROPN": handler__PROPN,
    "AUX": handler__VERB, # reuse aux handler for verb
    "VERB": handler__VERB,
    "PUNCT": handler__PUNCT,
    "SYM": handler__PUNCT # symbols are handled like punctuation
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

    # root indx to point the ending delimiter to
    root = 0

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
        deprel = word.deprel.upper()
        deprel = deprel.replace(":", "-")
        gra.append(f"{indx+1}|{word.head}|{deprel}")
        # if depedence relation is root, mark the current
        # ID as root
        if word.deprel.upper() == "ROOT":
            root = word.id

    # append ending delimiter to GRA
    gra.append(f"{len(sentence.words)+1}|{root}|PUNCT")

    mor_str = (" ".join(mor)).strip()
    gra_str = (" ".join(gra)).strip()

    # add the endning delimiter
    if len(mor_str) != 1: # if we actually have content (not just . or ?)
                          # add a deliminator
        mor_str = mor_str + " " + delimiter

    return (mor_str, gra_str)

def clean_sentence(sent):
    """clean a sentence 

    Arguments:
        sent (string): 
    """

    remove = ["+,", "++", "+\""]

    sent = sent

    # remove each element
    for i in remove:
        sent = sent.replace(i, "")

    return sent


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
                          download_method=DownloadMethod.REUSE_RESOURCES,
                          tokenize_no_ssplit=True)

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

            # clean the sentence
            line_cut = clean_sentence(line_cut)

            # if at this point we still have nothing, just
            # assume its an end punctuation (i.e. the whole
            # utterance was probably just ++ or something
            # that clean_sentence cut out

            if line_cut == "":
                line_cut = ending

            sents = nlp(line_cut).sentences

            sentences.append(
                # we want to treat the entire thing as one large sentence
                parse_sentence(sents[0], ending)
            )

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
        

      
