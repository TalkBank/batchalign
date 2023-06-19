# our utilities
from baln.dp import *
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

def __cleanstring(s, splittoken="|||"):
    s = s.replace("hmm", "hm")
    s = s.replace("mmhmm", "mhm")
    s = s.replace("mmhm", "mhm")
    s = s.replace("um", "uh")
    s = s.replace("selfemployed", f"self{splittoken}employed")
    s = s.replace("cuz", f"because")
    s = s.replace("gonna", f"going{splittoken}to")
    s = s.replace("wanna", f"want{splittoken}to")
    s = s.replace("'s", f"{splittoken}is")
    s = s.replace("shes", f"she{splittoken}is")
    s = s.replace("hes", f"he{splittoken}is")
    s = s.replace("dunno", f"dont{splittoken}know")
    s = s.replace("onto", f"on{splittoken}to")
    s = s.replace("hasta", f"has{splittoken}to")
    s = s.replace("kinda", f"kind{splittoken}of")
    s = s.replace("we're", f"we{splittoken}are")
    s = s.replace("'ve", f"{splittoken}have")
    s = s.replace("wouldve", f"would{splittoken}have")
    s = s.replace("coattails", f"coat{splittoken}tails")
    s = s.replace("exmarines", f"ex{splittoken}marines")
    s = s.replace(f"all{splittoken}right", f"alright")

    return s

def clean_resplit(arr):
    """Join an array, and perform blanket string replacements

    Attributes:
       arr (List[str)): the array to clean

    Returns:
        List[str]
    """

    return [i.strip() for i in
            __cleanstring("|||".join(arr)).split("|||")
            if i.strip() != ""]

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

    # get the text chunks, sorting by the start time of each text
    # we also match the words by their average time
    asr = [i[0] for i in filter(lambda x:x[1][1] <= minimum, asr)]
    transcript = [i[0] for i in filter(lambda x:x[1][1] <= minimum, transcript)]

    # break up the underscores _ from the transcript
    transcript = [j for i in transcript for j in i.split("_")]

    # perform some necessary filtering
    # lowercase everything
    asr = [i.lower() for i in asr]
    transcript = [i.lower() for i in transcript]

    # remove symbols
    asr = [re.sub(r"[^\w]", '', i).strip() for i in asr]
    transcript = [re.sub(r"[^\w]", '', i).strip() for i in transcript]

    # remove blank strings
    asr = [i for i in asr if i != ""]
    transcript = [i for i in transcript if i != ""]

    # and apply the fix
    asr = clean_resplit(asr)
    transcript = clean_resplit(transcript)

    # and diff! Recall WER is (substitution + deletion + insertion)/(number of words)
    raw_diff = align(asr, transcript)
    diff = []

    # generate human-readable diff
    for result in raw_diff:
        if type(result) == Match:
            diff.append(f"  {result.key}")
        elif type(result) == Extra and result.extra_type == ExtraType.PAYLOAD:
            diff.append(f"- {result.key}")
        elif type(result) == Extra and result.extra_type == ExtraType.REFERENCE:
            diff.append(f"+ {result.key}")

    # track change
    S = 0
    D = 0
    I = 0
    C = 0

    prev_minus = 0 # track if the PREVIOUS token was '-'
    for i in diff:
        # for each change, we could be '', '+', '-'
        diff_type = i.split(" ")[0]
        word = i.split(" ")[-1].strip()

        if diff_type == "?":
            continue

        # if previous is '-', and the next is '+', it is actually a substitution
        # concatenation is not technically an error, so if all the
        # minuses add up to the same plus, it is considered fine
        if ("firstname" in word) or ("lastname" in word):
            # detect and remove extra counts for
            # anonomization
            prev_minus = 0
            S -= 1
        elif diff_type=='+' and prev_minus:
            prev_minus = 0
            S += 1
        elif diff_type=='+':
            I += 1
        elif diff_type=='-':
            prev_minus += 1
            D += 1 
        elif diff_type == '':
            C += 1

    wer = round((S+D+I)/(S+D+C), 3)

    # https://en.wikipedia.org/wiki/Word_error_rate
    return wer, diff

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

    # first, perform alignment to get words/timestamp
    DATA_DIR = os.path.join(out_dir, data_directory)

    # Make the data directory if needed
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    TMPDEBUG = False
    if TMPDEBUG == False:
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
        # import pickle
        # with open("./tmp.bin", "wb") as df:
        #     pickle.dump([asr_words, transcript_words, aligned_results], df)

    else:
        import pickle
        with open("./tmp.bin", "rb") as df:
            asr_words, transcript_words, aligned_results = pickle.load(df)

    # get WER results
    WER = []

    for asr, transcript in zip(asr_words, transcript_words):
        WER.append(calculate_wer(asr, transcript))

    # featurize
    with open(os.path.join(out_dir, "benchmarks.csv"), 'w') as df:
        writer = csv.writer(df)
        writer.writerow(["file", "wer"])

        for (i, _), (wer, txt) in zip(aligned_results, WER):
            if not TMPDEBUG:
                os.rename(i, repath_file(i, DATA_DIR))
            writer.writerow([Path(i).stem, wer])
            # write the cut file
            with open(i.replace(".cha",".diff"), 'w') as cutfile:
                cutfile.write("\n".join(txt).strip())

    if clean:
        cleanup(in_dir, out_dir, data_directory)

    if TMPDEBUG:
        raise Exception("TMPDEBUG is on")



