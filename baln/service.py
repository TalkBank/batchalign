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

import sys

from enum import Enum
from dataclasses import dataclass

from multiprocessing import Process, Manager, Queue
from multiprocessing.connection import Connection
from multiprocessing.managers import DictProxy, AutoProxy

from tempfile import TemporaryDirectory
import tarfile

from loguru import logger as L

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
    lang: str = "en" # the two-letter ISO 639-1 language code 
    prealigned: bool = True # whether or not we should use the classic alignment algorithm
                            # where utterance segmentation is not needed. Default "don't",
                            # which means by default we would require utterance segmentation.
    beam: int = 30 # the alignment beam width

    # read only instruction ID for storage
    def __post_init__(self): 
        self.__id = str(uuid4())

    @property
    def id(self):
        return self.__id

def execute(instruction:BAInstruction, output_path:str, registry:DictProxy, mfa_mutex:AutoProxy):
    """Execute a BAInstruction, sending the output to the dictproxy registry

    Parameters
    ----------
    instruction : BAInstruction
        The batchalign instruction to execute.
    output_path: str
        Where to put the output tarballs
    registry : DictProxy
        A dictionary to store the output data.
    mfa_mutex : Lock
        Unfortunately, MFA's dependency on a local Posgres instance breaks some stuff.
        So we need to enforce the thread-safety of MFA by having one alignment operation
        runinng once.
    """

    # because we change into a temporary directory later
    output_path = os.path.abspath(output_path)
    in_dir = os.path.abspath(instruction.payload) # the input dir is just the payload

    # store temporary directory
    wd = os.getcwd()
    # create and change to temporary directory
    with TemporaryDirectory() as tmpdir:
        # change into temproary directory and do work
        os.chdir(tmpdir)
        # make a corpus output directory
        out_dir = os.path.join(tmpdir, instruction.corpus_name)
        os.mkdir(out_dir)

        # now, perform work depending on what type we are working with
        if instruction.command == BACommand.ALIGN:
            with mfa_mutex:
                do_align(in_dir, out_dir, prealigned=instruction.prealigned,
                        beam=instruction.beam, aggressive=True)
        elif instruction.command == BACommand.TRANSCRIBE:
            retokenize_directory(in_dir, noprompt=True, interactive=False, lang=instruction.lang)
            with mfa_mutex:
                do_align(in_dir, out_dir, prealigned=True, beam=instruction.beam, aggressive=True)
        elif instruction.command == BACommand.UD:
            morphanalyze(in_dir, out_dir, lang=instruction.lang)

        # create a tarball out of the output direcotry
        out_tar_path = os.path.join(output_path, f"{instruction.corpus_name}-{instruction.id}.tar.gz")
        with tarfile.open(out_tar_path, "w:gz") as tf:
            tf.add(f"./{instruction.corpus_name}")

        registry[instruction.id] = {
            "id": instruction.id,
            "status": "success",
            "payload": out_tar_path
        }

    # change directory back
    os.chdir(wd)

def worker_loop(output_path:str, tasks:Queue, registry:DictProxy, mfa_mutex:AutoProxy):
    """The function code for a worker thread"""
    while True:
        L.debug("Thread open!")
        instruction = tasks.get()
        L.info(f"Currently processing Instruction #{instruction.id}")
        try:
            execute(instruction, output_path, registry, mfa_mutex)
        except Exception as e:
            error_str = str(e)
            registry[instruction.id] = {
                "id": instruction.id,
                "status": "error",
                "payload": error_str
            }

        L.info(f"Done with Instruction #{instruction.id}")

def spawn_workers(output_path:str, tasks:Queue, registry:DictProxy, mfa_mutex:AutoProxy, num=5):
    """Function to spawn workers to perform work"""

    processes = []

    for _ in range(num):
        processes.append(Process(target=worker_loop, args=(output_path, tasks, registry, mfa_mutex)))

    for process in processes:
        process.start()

    return processes

# set up logging by removing the default logger and adding our own
L.remove()
L.add(sys.stdout, level="DEBUG", format="({time:YYYY-MM-DD HH:mm:ss}) <lvl>{level}</lvl>: {message}", enqueue=True)

# the input and output queues
if __name__ == "__main__":
    # set up the tools
    manager = Manager()
    registry = manager.dict()
    queue = manager.Queue()
    mfa_mutex = manager.Lock()

    # start!
    workers = spawn_workers("../opt/", tasks=queue, registry=registry, mfa_mutex=mfa_mutex, num=5)

    # send a fun task
    instruction0 = BAInstruction("test", BACommand.TRANSCRIBE, "../../talkbank-alignment/testing_playground_2/input")
    instruction1 = BAInstruction("test", BACommand.TRANSCRIBE, "../../talkbank-alignment/testing_playground_2/input")
    queue.put_nowait(instruction0)
    queue.put_nowait(instruction1)

    # aaaand block main thread execution
    for process in workers:
        process.join()

