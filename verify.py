""""
verify.py
Performs one-off human validation of aligned results from batchalign facilities
"""

# os utilities
import os
# pathing
import pathlib
# regex
import re
# glob
import glob
# argument
import argparse
# randomness
import random

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)

# NOTE THAT THE INPUT DIRECTORY MUST ONLY CONTAIN .WAVS AND .CHA,
# NOTHING ELSE SHOULD BE INSIDE THE INPUT DIRECTORY!

# temp directory to verify
verify = "../RevTest4/out"

# open the temp files for writing
matched_files = list(zip(sorted(globase(verify, "*.cha")), sorted(globase(verify, "*.wav"))))

# function to play sound
def playsound(f, start, end):
    """Function to play a sound with ffplay

    Arguments:
        f (str): file to play
        start (int): integer in ms where to start
        end (int): integer in ms where to end
    """

    CMD = f"ffplay {f} -vn -t {(end-start)/1000} -ss {start/1000} -nodisp -autoexit &"
    os.system(CMD)




