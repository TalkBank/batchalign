# our tools
from baln.utils import *
from baln.fa import do_align
from baln.retokenize import retokenize_directory
from baln.ud import morphanalyze

# flasky tools
from werkzeug.utils import secure_filename
from flask import Flask, flash, request, redirect, url_for

# python tools
from uuid import uuid4

from enum import Enum
from dataclasses import dataclass

from multiprocessing import Process, Queue, Pipe
from multiprocessing.connection import Connection

from tempfile import TemporaryDirectory
import tarfile

# command dataclass
class BACommand(Enum):
    TRANSCRIBE = 0
    ALIGN = 1
    UD = 2

@dataclass
class BAInstruction:
    corpus_name: str # string name for the corpus
    command: BACommand # batchalign command to use
    payload: str # the input directory; the outdir is temproray
    lang: str # the two-letter ISO 639-1 language code 
    prealigned: bool = True # whether or not we should use the classic alignment algorithm
                            # where utterance segmentation is not needed. Default "don't",
                            # which means by default we would require utterance segmentation.
    beam: int = 30 # the alignment beam width


def execute(instruction:BAInstruction, channel:Connection):
    """Execute a BAInstruction, sending the output to channel

    Parameters
    ----------
    instruction : BAInstruction
        The batchalign instruction to execute.
    channel : Connection
        The channel to send the byte-encoded tarball of the output to.
    """
    

    # store temporary directory
    wd = os.getcwd()
    # create and change to temporary directory
    with TemporaryDirectory() as tmpdir:
        # change into temproary directory and do work
        os.chdir(tmpdir)
        # make a corpus output directory
        in_dir = instruction.payload # the input dir is just the payload
        out_dir = os.path.join(tmpdir, instruction.corpus_name)

        # now, perform work depending on what type we are working with
        if instruction.command == BACommand.ALIGN:
            do_align(in_dir, out_dir, prealigned=instruction.prealigned,
                     beam=instruction.beam, aggressive=True)
        elif instruction.command == BACommand.TRANSCRIBE:
            retokenize_directory(in_dir, noprompt=True, interactive=False, lang=instruction.lang)
            do_align(in_dir, out_dir, prealigned=True, beam=instruction.beam, aggressive=True)
        elif instruction.command == BACommand.UD:
            morphanalyze(in_dir, out_dir, lang=instruction.lang)

        # create a tarball out of the output direcotry
        with tarfile.open(f"./{instruction.corpus_name}.tar.gz", "w:gz") as tf:
            tf.add(out_dir)

        with open(f"./{instruction.corpus_name}.tar.gz", "rb") as df:
            channel.send_bytes(df.read())

    # change directory back
    os.chdir(wd)


# the input and output queues
TASK_QUEUE = Queue()
DONE_rx, DONE_tx = Pipe(duplex=False)

