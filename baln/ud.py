# system utils
import glob, os, re

# pathing tools
from pathlib import Path

# UD tools
import stanza

from stanza import Document
from stanza.models.common.doc import Token
from stanza.pipeline.core import CONSTITUENCY
from stanza import DownloadMethod
from torch import heaviside

from stanza.pipeline.processor import ProcessorVariant, register_processor_variant

# the loading bar
from tqdm import tqdm

from nltk import word_tokenize
from collections import defaultdict

# out utiltiies
from .utils import *
from .eaf import *
from .dp import *

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)

# Register tokenizer processor variant, and fix tokenization for specific forms
@register_processor_variant("tokenize", "ba")
class BATokenizer(ProcessorVariant):

    OVERRIDE = True

    def __init__(self, config):
        self.__subpipe = stanza.Pipeline(lang=config["lang"],
                                         processors='tokenize')
        self.__lang = config["lang"]

    def process(self, text):
        # for sentence in document.sentences:
        #     for word in sentence.words:
        #         word.lemma = "cool"
        if text.strip() == '':
            text = "."

        document = self.__subpipe(text) 

        try:
            neural_tokens = [[j.text for j in i.words] for i in document.sentences[0].tokens]
        except IndexError:
            breakpoint()

        structural_text = text
        structural_text = structural_text.replace("l'  ", "l'")
        structural_text = structural_text.replace("l'", "l' ")
        structural_text = structural_text.replace("nell'", "nell' ")
        structural_text = structural_text.replace("all'", "all' ")
        structural_text = structural_text.replace("dall'", "dall' ")
        structural_tokens = [i for i in structural_text.split(" ")
                             if i != ""]

        aligned = list(zip(structural_tokens, neural_tokens))

        # this should be in the format of
        # [ (structural_token: [semantic, tokens]), ...]

        # we now perform language specific post-processing
        aligned = self.__tok_reprocess(aligned)

        # assemble stanza-compatible final output
        # taking care to treat multi-word tokens the way Stanza
        # expects; run a mwt through stanza to see
        # how they want it
        final_tokens = []
        current_token_index = 1
        for text, tokens in aligned:
            final_tokens.append({
                "id": (current_token_index,
                       current_token_index+len(tokens)-1)
                if len(tokens) > 1 else (current_token_index, ),
                "text": text})
            current_token_index = current_token_index+len(tokens)

        try:
            reconstructed = Document([final_tokens], text)
        except:
            breakpoint()
        return reconstructed

    def __tok_reprocess(self, aligned):
        if self.__lang == "it":
            return self.__tok_reprocess__it(aligned)

        # if no processor is registered, just return the
        # original sequence
        return aligned

    def __tok_reprocess__it(self, aligned):

        new = []

        for key, value in aligned:
            fixed = value
            if key == "dai":
                fixed = ["dai"]
            elif key == "dài":
                fixed = ["dài"]
            elif key == "aòe":
                fixed = ["aòe"]

            new.append((key, fixed))

        return new
        

# one liner to parse features
def parse_feats(word):
    try:
        return {i.split("=")[0]: i.split("=")[1] for i in word.feats.split("|")}
    except AttributeError:
        return {}
# one liner to join feature string
def stringify_feats(*feats):
    template= ("-"+"-".join(filter(lambda x: x!= "", feats))).strip()

    if template == "-": return ""
    else: return template.replace(",", "")

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
    if not target:
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

    target = target.replace("$", "")
    target = target.replace(".", "")

    # if we have a clitic that's broken off, we remove the extra dash
    if target != "" and target[0] == "-":
        target = target[1:]

    target = target.replace(',', '')

    # remove attachments
    if "|" in target:
        target = target.split("|")[0].strip()

    # clean out alternate spellings

    return f"{'' if not unknown else '0'}{word.upos.lower()}|{target}"

# POS specific handler
def handler__PRON(word):
    # get the features
    feats = parse_feats(word)
    # parse
    return (handler(word)+"-"+
            feats.get("PronType", "Int")+"-"+
            feats.get("Case", "Acc").replace(",", "")+"-"+
            feats.get("Number", "S")[0]+str(feats.get("Person", 1)))

def handler__DET(word):
    # get the features
    try:
        feats = parse_feats(word)
    except AttributeError:
        return handler(word)
    # parse
    return (handler(word)+"-"+
            feats.get("Definite", "Def") + stringify_feats(feats.get("PronType", "")))

def handler__ADJ(word):
    # get the features
    feats = parse_feats(word)
    # if there is a non-degree
    deg = feats.get("Degree", "Pos")
    case = feats.get("Case", "").replace(",", "")
    number = feats.get("Number", "S")[0]
    person = str(feats.get("Person", 1))
    return handler(word)+stringify_feats(deg, case, number, person)

def handler__NOUN(word):
    # get the features
    feats = parse_feats(word)

    # get gender and numer
    gender_str = "&"+feats.get("Gender", "ComNeut").replace(",", "")
    number_str = "-"+feats.get("Number", "Sing")
    case  = feats.get("Case", "").replace(",", "")
    type  = feats.get("PronType", "")


    # clear defaults
    if gender_str == "&Com,Neut" or gender_str == "&Com": gender_str=""
    if number_str == "-Sing": number_str=""

    return handler(word)+gender_str+number_str+stringify_feats(case, type)

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
    flag += "-"+feats.get("VerbForm", "Inf").replace(",", "")
    number = feats.get("Number", "Sing")
    if number != "Sing":
        flag += f"-{number}"
    # append tense
    aspect = feats.get("Aspect", "")
    mood = feats.get("Mood", "")
    person = feats.get("Person", "")
    tense = feats.get("Tense", "")
    polarity = feats.get("Polarity", "")
    polite = feats.get("Polite", "")
    return handler(word)+flag+stringify_feats(aspect, mood, person,
                                              tense, polarity, polite)

def handler__actual_PUNCT(word):
    # actual punctuation handler
    if word.lemma=="," or word.lemma=="$,":
        return "cm|cm"
    elif word.lemma in ['.', '!', '?']:
        return word.lemma
    elif word.text in '‡':
        return "end|end"
    elif word.text in '„':
        return "end|end"

    # all other cases return None
    # to skip

def handler__PUNCT(word):
    # no idea why SYM and PUNCT returns punctuation
    # or sometimes straight up words, but  so it goes
    # either punctuation or inflection words
    if word.lemma in ['.', '!', '?', ',', '$,']:
        return handler__actual_PUNCT(word)
    elif word.text in ['„', '‡']:
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
def parse_sentence(sentence, delimiter=".", special_forms=[], lang="$nospecial$"):
    """Parses Stanza sentence into %mor and %gra strings

    Arguments:
        sentence: the stanza sentence object
        [delimiter]: the default delimiter to use to end utterances
        [special_forms]: a list of special forms to replace back
        [lang]: language we are working with

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

    # counter for number of words skipped
    actual_indicies = []
    num_skipped = 0

    # generating temp "gra" data (array numerical, before shift
    # correction)
    gra_tmp = []

    # keep track of mwts
    mwts = []
    clitics = []
    # locations of elements with -ce, -être, -là
    # needs to be joined
    auxiliaries = []


    # TODO jank 2O(n) parse!
    # get mwts
    for indx, token in enumerate(sentence.tokens):

        if token.text[0]=="-":

            # we have to subtract 1 becasue $ goes to the
            # NEXT element
            auxiliaries.append(token.id[0]-1)

        if len(token.id) > 1:
            mwts.append(token.id)

        if token.text.strip() == "l'":
            clitics.append(token.id[0])
        elif lang=="it" and token.text.strip()[-3:] == "ll'":
            auxiliaries.append(token.id[-1])
        elif lang=="it" and token.text.strip() == "gliel'":
            auxiliaries.append(token.id[-1])
        elif lang=="it" and token.text.strip() == "qual'":
            auxiliaries.append(token.id[-1])
        elif lang=="fr" and token.text.strip() == "qu'":
            auxiliaries.append(token.id[-1])
        elif lang=="fr" and token.text.strip() == "jusqu'":
            auxiliaries.append(token.id[-1])
        elif lang=="fr" and token.text.strip() == "au":
            auxiliaries.append(token.id[0])
        elif lang=="fr" and token.text.strip() == "aux":
            auxiliaries.append(token.id[0])
        elif lang=="fr" and token.text.strip() == "du":
            auxiliaries.append(token.id[0])
        elif lang=="fr" and len(token.text.strip()) == 2 and token.text.strip()[-1] == "'":
            auxiliaries.append(token.id[-1])

    # because we pop from it
    special_forms = special_forms.copy()
    special_form_ids = []
    # get words
    for indx, word in enumerate(sentence.words):
        # append the appropriate mor line
        # by trying all handlers, and defaulting
        # to the default handler
        mor_word = HANDLERS.get(word.upos, handler)(word)
        # exception: if the word is 0, it is probably 0word
        # occationally Stanza screws up and makes forms like 0thing as 2 tokens:
        # 0 and thing 
        if word.text.strip() == "0":
            mor.append("$ZERO$")
            num_skipped+=1 # mark skipped if skipped
            actual_indicies.append(root) # TODO janky but if anybody refers to a skipped
                                         # word they are root now.
        # normal parsing
        elif mor_word:
            # specivl forms: recall the special form marker is xbxxx
            if word.text.strip() == "xbxxx":
                form = special_forms.pop(0)
                mor.append(f"x|{form.strip()}")
                special_form_ids.append(word.id)
            else:
                mor.append(mor_word)
            # +1 because we are 1-indexed
            # and .head is also 1-indexed already
            deprel = word.deprel.upper()
            deprel = deprel.replace(":", "-")
            gra_tmp.append(((indx+1)-num_skipped, word.head, deprel))
            actual_indicies.append((indx+1)-num_skipped) # so we can check later
            # if depedence relation is root, mark the current
            # ID as root
            if word.deprel.upper() == "ROOT":
                root = ((indx+1)-num_skipped)
        # some handlers may return None to skip the word
        else:
            mor.append(None)
            num_skipped+=1 # mark skipped if skipped
            actual_indicies.append(root) # TODO janky but if anybody refers to a skipped
                                         # word they are root now.

    # and now for each element, we shift and generate
    # recall that indicies are one indexed
    for i, elem in enumerate(gra_tmp):
        # if we are at a special form ID, append a special form mark instead
        if elem[0] in special_form_ids:
            elem = (elem[0], elem[1], "FLAT")
        # the third element is responsible for looking up the correctly
        # shifted index for the item in question
        gra.append(f"{elem[0]}|{actual_indicies[elem[1]-1]}|{elem[2]}")

    # append ending delimiter to GRA
    gra.append(f"{len(sentence.words)+1-num_skipped}|{root}|PUNCT")

    mor_clone = mor.copy()

    # we will join all the segments with ' in the end with
    # a dollar sign because those are considered
    # one word
    # recall again one indexing
    while len(clitics) > 0:
        clitic = clitics.pop()
        try:
            mor_clone[clitic-1] = mor_clone[clitic-1]+"$"+mor_clone[clitic]
        except IndexError:
            breakpoint()
        mor_clone[clitic] = None

    # connect auxiliaries with a "~"
    # recall 1 indexing
    for aux in auxiliaries:
        # if the previous one was joined,
        # we keep searching backwards

        orig_aux = aux
        while not mor_clone[aux-1]:
            aux -= 1

        if mor_clone[orig_aux]:
            mor_clone[aux-1] = mor_clone[aux-1]+"~"+mor_clone[orig_aux]
            mor_clone[orig_aux] = None

    while len(mwts) > 0:
        # handle MWTs
        # TODO assumption MWTs are continuous
        mwt = mwts.pop(0)
        mwt_start = mwt[0]
        mwt_end = mwt[-1]

        # why the copious -1s? One indexing

        # combine results
        mwt_str = "~".join([i for i in mor_clone[mwt_start-1:mwt_end] if i])

        # delete old
        for j in range(mwt_start, mwt_end+1):
            mor_clone[j-1] = None

        # replace in new dict
        mor_clone[mwt_start-1] = mwt_str

    mor_str = (" ".join(filter(lambda x:x, mor_clone))).strip().replace(",", "")
    gra_str = (" ".join(gra)).strip()

    # handle special zeros, see $ZERO$ above
    mor_str = mor_str.replace("$ZERO$ ","0")

    # add the endning delimiter
    if len(mor_str) != 1: # if we actually have content (not just . or ?)
                          # add a deliminator
        mor_str = mor_str + " " + delimiter


    mor_str = mor_str.replace("<UNK>", "")
    gra_str = gra_str.replace("<UNK>", "")

    # empty utterances fix
    if mor_str.strip() in ["+//.", "+//?", "+//!"]:
        mor_str=None

    if mor_str == None:
        mor_str = ""
    if gra_str == None:
        gra_str = ""

    if mor_str.strip() == "" or gra_str.strip() == "" or mor_str.strip()==".":
        mor_str = ""
        gra_str = ""

    return (mor_str, gra_str)

def clean_sentence(sent):
    """clean a sentence 

    Arguments:
        sent (string): 
    """

    remove = ["+,", "++", "+\"", "_"]

    sent = sent

    # remove each element
    for i in remove:
        sent = sent.replace(i, "")

    return sent


def morphanalyze(in_dir, out_dir, data_dir="data", lang="en", clean=True, aggressive=None):
    """Batch morphosyntactic analysis tools using Stanza

    Arguments:
        in_directory (string): the directory containing .cha and .wav/.mp3 file
        out_directory (string): the directory for the output files
        [language (string)]: what language are we analyzing?
        [data_directory (string)]: the subdirectory (rel. to out_directory) which the misc.
                                   outputs go
        [clean (bool)]: whether to clean up, used for debugging
        [aggressive (bool)]: useless option to satisfy interface

    Returns:
        none
    """

    # Define the data_dir
    DATA_DIR = os.path.join(out_dir, data_dir)

    # Make the data directory if needed
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    print("Starting Stanza...")

    nlp = stanza.Pipeline(lang,
                          processors={"tokenize": "default",
                                      "pos": "default",
                                      "lemma": "default",
                                      "depparse": "default"},
                          tokenize_no_ssplit=True)

    # create label and elan files
    chat2transcript(in_dir, True)
    chat2elan(in_dir, False)

    # process each file
    print("Performing analysis...")
    for f in globase(in_dir, "*.cha"):
        print(f"Tagging {Path(f).stem}.cha...")

        # get file names
        label_file = f.replace(".cha", ".lab")
        elan_file = f.replace(".cha", ".eaf")
        elan_target = repath_file(elan_file, out_dir)

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
            # ending = ending.replace("+//", "")

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

            line_cut = line_cut.replace("+<", "")
            line_cut = line_cut.replace("+/", "")
            line_cut = line_cut.replace("(", "")
            line_cut = line_cut.replace(")", "")
            line_cut = line_cut.replace("+^", "")
            line_cut = line_cut.replace("_", "")
            line_cut = line_cut.replace("+//", "")

            # xbxxx is a sepecial xxx-class token to mark
            # special form markers, used for processing later
            # down the line
            special_forms = re.findall(r"\w+@[\w\:]+", line_cut)
            special_forms_cleaned = []
            for form in special_forms:
                line_cut = line_cut.replace(form, "xbxxx")
                special_forms_cleaned.append(re.sub(r"@[\w\:]+", "", form).strip())

            # if line cut is still nothing, we get very angry
            if line_cut == "":
                line_cut = ending

            # Norwegian apostrophe fix
            if line_cut[-1] == "'":
                line_cut = line_cut[:-1]
                
            line_cut = line_cut.replace(",", " ,")
            line_cut = line_cut.replace("+ ,", "+,")
            line_cut = line_cut.replace("  ", " ")
            line_cut = line_cut.replace("c'est", "c' est")
            line_cut = line_cut.replace("d'", "d' ")

            sents = nlp(line_cut).sentences
            # breakpoint()

            if len(sents) == 0:
                sents = ["."]
            else:
                sentences.append(
                    # we want to treat the entire thing as one large sentence
                    parse_sentence(sents[0], ending, special_forms_cleaned, lang)
                )

        # inject into EAF
        # we have no MFA alignments, instead, we are injecting
        # morphological data
        eafinject(elan_file, elan_target,
                   alignments=None,
                   morphodata=sentences)

    # convert the prepared eafs back into chat
    elan2chat(out_dir)

    # general final transcript bullet correction
    # this also removes the @Options: heritage label and corrects for -1
    for f in globase(out_dir, "*.cha"):
        check_media_link(f)

    # cleanup!
    if clean:
        cleanup(in_dir, out_dir, data_dir)

