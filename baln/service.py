# our tools
from baln.utils import *
from baln.fa import do_align
from baln.retokenize import retokenize_directory
from baln.ud import morphanalyze

# flasky tools
from werkzeug.utils import secure_filename
from flask import Flask, flash, request, redirect, url_for, send_file
from flask_cors import cross_origin
from werkzeug.utils import secure_filename

# python tools
from uuid import uuid4

import sys

from datetime import datetime

from enum import Enum
from dataclasses import dataclass

from multiprocessing import Process, Manager, Queue, cpu_count, freeze_support
from multiprocessing.connection import Connection
from multiprocessing.managers import DictProxy, AutoProxy

from tempfile import TemporaryDirectory
import tarfile

from loguru import logger as L

from gunicorn.app.base import BaseApplication

# util to calculate number of works
def number_of_workers():
    return (cpu_count() * 2) + 1

# create the api object
app = Flask("batchalign")

# gunicorn application boilerplate
class BatchalignGunicornService(BaseApplication):
    def __init__(self, app, ip="0.0.0.0", port="8080", workers=5):
        self.options = {"preload_app": True,
                        "bind": f"{ip}:{port}",
                        "workers": workers}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

# command dataclass
class BACommand(Enum):
    TRANSCRIBE = "transcribe"
    ALIGN = "align"
    UD = "morphotag"

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
        self.__id = str(uuid4())[:8] 

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        self.__id = id

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
        out_tar_path = os.path.join(output_path, f"{instruction.corpus_name}-{instruction.id}-output.tar.gz")
        with tarfile.open(out_tar_path, "w:gz") as tf:
            tf.add(f"./{instruction.corpus_name}")

        registry[instruction.id] = {
            "id": instruction.id,
            "name": instruction.corpus_name,
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
                "name": instruction.corpus_name,
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

@app.route('/jobs/<id>', methods=['GET'])
@cross_origin()
def jobs(id):
    try: 
        # return the result
        data =  app.config["REGISTRY"][id.strip()]

        res =  {
            "id": data.get("id"),
            "status": data.get("status"),
            "name": data.get("name"),
        }

        if data.get("status") == "error":
            res["payload"] = data.get("payload")

        return res

    except KeyError:
        return {
            "status": "not_found",
            "message": "That's not an ID we are used to! Check your input arguments please."
        }, 404

@app.route('/download/<id>', methods=['GET'])
@cross_origin()
def download(id):
    try: 
        # return the result
        data = app.config["REGISTRY"][id.strip()]

        if data["status"] != "success":
            return {
                "status": "error",
                "message": "That file is not ready yet or has errored; please use /jobs/<id> to check on its status."
            }, 400

        return send_file(data["payload"])

    except KeyError:
        return {
            "status": "not_found",
            "message": "that's not an ID we are used to! check your input please"
        }, 404

@app.route('/submit', methods=['POST'])
@cross_origin()
def submit():
    try: 
        # get the parameters from form info
        corpus_name = request.form["name"]
        command = request.form["command"]
        lang = request.form.get("lang", "en")

        # create the new instruction's ID
        id = str(uuid4())[:8]

        # create the input folder
        input_path = os.path.join(app.config["DATA_PATH"], f"{corpus_name}-{id}-input")
        os.mkdir(input_path)

        # save the input files
        for file in request.files.getlist("input"):
            filename = secure_filename(file.filename)
            file.save(os.path.join(input_path, filename))

        # create the instruction
        instruction = BAInstruction(corpus_name, BACommand(command), input_path, lang=lang)
        instruction.id = id

        # and submit it!
        app.config["QUEUE"].put_nowait(instruction)

        # write it down
        res = {
            "id": instruction.id,
            "name": corpus_name,
            "status": "processing"
        }

        app.config["REGISTRY"][instruction.id] = res

        # return the result
        return res, 200

    except ValueError:
        return {
            "status": "error",
            "message": "it looks like there was a malformed request, check your input arguments"
        }, 400

# set up logging by removing the default logger and adding our own
L.remove()
L.add(sys.stdout, level="INFO", format="({time:YYYY-MM-DD HH:mm:ss}) <lvl>{level}</lvl>: {message}", enqueue=True)

# the input and output queues
def run_service(data_path, ip="0.0.0.0", port=8080, num_workers=5):
    # magic to make sure things don't break
    freeze_support()

    # application tools
    manager = Manager()
    registry = manager.dict()
    queue = manager.Queue()
    mfa_mutex = manager.Lock()

    # set things
    app.config["QUEUE"] = queue
    app.config["REGISTRY"] = registry
    app.config["DATA_PATH"] = data_path

    # start batchalign workers
    workers = spawn_workers(data_path, tasks=queue, registry=registry,
                            mfa_mutex=mfa_mutex, num=num_workers)
    # start gunicorn workers
    BatchalignGunicornService(app, ip, port, num_workers).run()

    # aaaand block main thread execution
    for process in workers:
        process.join()

