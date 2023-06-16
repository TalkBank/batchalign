# our utilities
from baln.fa import *
from baln.utils import *
from baln.retokenize import *

# audio tools 
import numpy as np
import scipy.io.wavfile as wavfile

# import the tokenization engine
from baln.utokengine import UtteranceEngine

# their utilities
import re
import os
import csv
import json
import time
import string
from pathlib import Path
from urllib import request

# difflib
from difflib import Differ

def norm(f):
    """Gets the normalized audio signal from a file

    Attributes:
        file (str): the file to read

    Returns:
        np array
    """
    data = wavfile.read(f)[1]
    singleChannel = data
    try:
        singleChannel = np.sum(data, axis=1)
    except:
        # was mono after all
        pass

    norm = singleChannel / (max(np.amax(singleChannel), -1 * np.amin(singleChannel)))
    return norm

def signaltonoise(a, axis=0, ddof=0):
    """Calculates decibel signal to noise

    Attributes:
        a (np.Array): the array to compute snr
        [axis] (int): axis to compute
        [ddof] (int): ???

    Returns:
        float
    """
    m = a.mean(axis)
    sd = a.std(axis=axis, ddof=ddof)
    return 20*np.log10(abs(np.where(sd == 0, 0, m/sd)))

def calculate_wer(asr, transcript):
    """Calculates word error rate between two samples

    Attributes:
        asr (List[Tuple[str, Tuple[float,float]]]): the ASR output, encoded as a list of
                                                    words + start/end timing (ms)
        transcript (List[Tuple[str, Tuple[float,float]]]): the words and timing (ms) of the actual transcript 

    Notes:
        Note that this function uses the timing 

    Returns:
        Tuple[float, list], the WER value, and difflist
    """

    # cut to minimum possible time
    minimum = min(asr[-1][1][1],
                  transcript[-1][1][1])

    # get the text chunks
    asr = [i[0] for i in filter(lambda x:x[1][1] <= minimum, asr)]
    transcript = [i[0] for i in filter(lambda x:x[1][1] <= minimum, transcript)]

    # break up the underscores _ from the transcript
    transcript = [j for i in transcript for j in i.split("_")]

    # perform some necessary filtering
    # lowercase everything
    asr = [i.lower() for i in asr]
    transcript = [i.lower() for i in transcript]

    # remove symbols
    asr = [re.sub(r'[^\w]', '', i).strip() for i in asr]
    transcript = [re.sub(r'[^\w]', '', i).strip() for i in transcript]

    # remove blank strings
    asr = [i for i in asr if i != ""]
    transcript = [i for i in transcript if i != ""]

    # and diff! Recall WER is (substitution + deletion + insertion)/(number of words)
    diff = Differ().compare(asr, transcript)

    # ['- I', '+ i', '  ask', '  people', "  who've", '  had', '  strokes', '- to', '+ <to', '? +\n', '  tell', '- me', '+ me>', '?   +\n', '+ uh', '  to', '  tell', '  me', '  what', '  they', '  remember', '  about', '  when', '  they', '  had', '  their', '  stroke', '  since', '  you', "  haven't", '  had', '  a', '  stroke', '  i', '  wonder', '  if', '  you', '  could', '  tell', '  me', '  what', '  you', '  remember', '  about', '  any', '  illness', '  or', '  injury', "  you've", '  had', '- Um', '+ um', '  back', '  in', '  two', '  thousand', '  and', '  nine', '  i', '  had', '  shingles', '  and', '  that', '  was', '  extremely', '  painful', '- i', '- sir', '- was', '+ and', '+ it', '+ started', '+ with', '  a', '  small', '  blister', '  that', '  came', '  up', '  on', '  the', '  side', '  of', '  my', '  head', '  and', "  i'd", '  just', '  been', '  to', '  nicaragua', '  so', '  i', '  thought', '- hmm', '?   -\n', '+ hm', '  did', '  i', '  get', '  something', '  really', '  creepy', '  down', '  there', '  um', '  but', '  then', '  it', '  just', '  started', '  getting', '  worse', '  and', '  i', '  started', '  having', '  extreme', '  headaches', '  and', '  went', '  to', '  the', '  doctor', '  found', '  out', '- i', '+ it', '  was', '  shingles', '- Um', '+ um', '- Tell', '? ^\n', '+ tell', '? ^\n', '  me', '  about', '  your', '  recovery', '  from', '  that', '  illness', '- Um', '+ um', '  i', '- spent', '?     ^\n', '+ spend', '?     ^\n', '  a', '  couple', '  days', '  in', '  bed', '  um', '  really', '  bad', '  headaches', '  like', "  didn't", '  even', '  wanna', '  move', '- kinda', '+ kind_of', '  like', '  a', '  migraine', '  type', '  of', '  headache', '  um', '  took', '  medication', '  um', '+ i', '  was', '  glad', '  my', '  mom', '  was', '  visiting', '- cuz', '+ because', '  she', '- would', '? ^\n', '+ could', '? ^\n', '  bring', '  me', '  the', '  things', '  that', '  i', '  needed', '- but', '  i', '  slept']

    # track change
    S = 0
    D = 0
    I = 0
    C = 0

    prev_minus = False # track if the PREVIOUS token was '-'
    for i in diff:
        # for each change, we could be '', '+', '-'
        diff_type = i.split(" ")[0]

        if diff_type == "?":
            continue

        # if previous is '-', and the next is '+', it is actually a substitution
        if diff_type=='+' and prev_minus:
            prev_minus = False
            S += 1
        elif diff_type=='+':
            I += 1
        elif diff_type=='-':
            prev_minus = True
            D += 1 
        elif diff_type == '':
            C += 1

    # https://en.wikipedia.org/wiki/Word_error_rate
    return round((S+D+I)/(S+D+C), 3), list(Differ().compare(asr, transcript))

def benchmark_directory(in_dir, out_dir, data_directory="data", model_path=os.path.join("~","mfa_data","model"),
                        lang="en", beam=10, align=True, clean=True):
    """Calculate WER benchmarks from a directory.

    Attributes:
        in_directory (str): input directory containing files
        model_path (str): path to a BertTokenizer and BertModelForTokenClassification
                          trained on the segmentation task.
        [interactive] (bool): whether to run the interactive routine
        [lang] (str): language
        [noprompt] (bool): whether or not to provide no prompt

    Returns:
        None, used for .cha file generation side effects.
    """


    # check if model exists. If not, download it if needed.
    if not model_path and not os.path.exists(os.path.expanduser(defaultmodel("model"))):
        print("Getting segmentation model...")
        # make the path
        os.makedirs(os.path.expanduser(defaultfolder), exist_ok=True)
        # download the tarball
        model_data = request.urlopen(MODEL_PATH)
        # put it down
        model_zip = os.path.expanduser(defaultmodel("model.tar.gz"))
        with open(model_zip, 'wb') as df:
            df.write(model_data.read())
        # open it
        tar = tarfile.open(model_zip, "r:gz")
        tar.extractall(os.path.expanduser(defaultfolder))
        tar.close()
        # and then rename it
        basepath = os.path.expanduser(defaultfolder)
        os.rename(os.path.join(basepath, MODEL), os.path.join(basepath, "model"))

    # if a None was explicitly passed in
    if not model_path:
        model_path = os.path.join("~","mfa_data","model")

    # first, perform alignment to get words/timestamp
    DATA_DIR = os.path.join(out_dir, data_directory)

    # Make the data directory if needed
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    ### PREPATORY OPS ###
    # convert all mp3s to wavs
    wavs = globase(in_dir, "*.wav")
    # if there are no wavs, convert
    if len(wavs) == 0 and len(globase(in_dir, "*.mp4")) > 0:
        mp42wav(in_dir)
        # indeed, is video!
        is_video = True
    elif len(wavs) == 0: 
        mp32wav(in_dir)

    # Generate elan elan elan elan
    chat2elan(in_dir)

    # generate utterance and word-level alignments
    elans = globase(in_dir, "*.eaf")

    # convert all chats to TextGrids
    chat2praat(in_dir)

    # if we are to align
    if align:
        # Align the files
        align_directory_mfa(in_dir, DATA_DIR, beam=beam, lang=lang)

    # find textgrid files
    alignments = globase(DATA_DIR, "*.TextGrid")

    # store aligned files
    aligned_results = []

    # zip the results and dump into new eafs
    print("Done with MFA! Generating final word-level alignments and bullets...")
    for alignment in tqdm(sorted(alignments)):
        # Find the relative elan file
        elan = repath_file(alignment, in_dir).replace("TextGrid", "eaf").replace("textGrid", "eaf")
        # Align the alignment results
        # MFA TextGrids are long form
        print(f"Processing {alignment.replace('.TextGrid', '')}...")
        aligned_result = transcript_word_alignment(elan, alignment, alignment_form="long", aggressive=False)

        aligned_results.append((repath_file(alignment.replace('.TextGrid', ''), out_dir)+".cha",
                                aligned_result["raw"]))

    # so, we will convert the input directory to
    # seed an utterance engine to use
    Engine = UtteranceEngine(os.path.expanduser(model_path))

    # for each output results, we will go through and also ASR it
    asr_words = []
    for path, _ in aligned_results:
        # ASR!
        asr, header, main, closing = retokenize(repath_file(path, in_dir).replace('.cha', '.wav'), path, Engine,
                                                False, lang=lang, noprompt=True)
        asr_words.append([j for i in main for j in i[1]])

    transcript_words = []
    # also, parse the transcripts words by flattening the whole array
    for _,result in aligned_results:
        transcript_words.append([[j[0].lower(), [int(k*1000) for k in j[1]]]
                                for i in result
                                for j in i if j[1]])

    # get WER results
    WER = []

    for asr, transcript in zip(asr_words, transcript_words):
        WER.append(calculate_wer(asr, transcript))

    # featurize
    with open(os.path.join(out_dir, "benchmarks.csv"), 'w') as df:
        writer = csv.writer(df)
        writer.writerow(["file", "wer"])

        for (i, _), (wer, txt) in zip(aligned_results, WER):
            os.rename(i, repath_file(i, DATA_DIR))
            writer.writerow([Path(i).stem, wer])
            # write the cut file
            with open(i.replace(".cha",".diff"), 'w') as cutfile:
                cutfile.write("\n".join(txt).strip())

    if clean:
        cleanup(in_dir, out_dir, data_directory)



