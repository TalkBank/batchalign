import click
import functools

from multiprocessing import Process, freeze_support

VERSION="0.2.29"
NOTES="experimental signal to noise ratio"

#################### OPTIONS ################################

# common options for batchalign
def common_options(f):
    options = [
        click.argument("in_dir",
                       type=click.Path(exists=True, file_okay=False)),
        click.argument("out_dir",
                       type=click.Path(exists=True, file_okay=False)),
        click.option("--aggressive",
                     help="use dynamic programming to aggressivly align audio",
                     is_flag=True,
                     default=False,
                     type=str),
        click.option("--lang",
                     help="sample language in two-letter ISO 639-1 code",
                     show_default=True,
                     default="en",
                     type=str),
        click.option("--clean/--skipclean",
                     help="sweep stray files from input/output directory to data",
                     default=True)
    ]
    options.reverse()
    return functools.reduce(lambda x, opt: opt(x), options, f)

###################### UTILS ##############################

@click.group()
@click.pass_context
def batchalign(ctx):
    """batch process CHAT files in IN_DIR and dumps them to OUT_DIR"""

    ## setup commands ##
    # multiprocessing thread freeze
    freeze_support()
    # ensure that the contex object is a dictionary
    ctx.ensure_object(dict)

#################### ALIGN ################################

@batchalign.command()
@common_options
@click.pass_context
@click.option("--beam", type=int,
              default=30, help="beam width for MFA")
@click.option("--align/--skipalign",
              help="actually invoke MFA or just run Batchalign operations", default=True)
@click.option("--prealigned/--scratch",
              help="process CHAT file that is already utterance aligned", default=True)
def align(ctx, **kwargs):
    """align a CHAT transcript against a media file"""

    # forced alignment tools
    from .fa import do_align

    # report status
    click.echo("Performing forced alignment...")

    # forced align!
    do_align(**kwargs)

#################### TRANSCRIBE ################################

@batchalign.command()
@common_options
@click.pass_context
@click.option("--align/--skipalign",
              help="actually invoke MFA or just run ASR", default=True)
@click.option("-i", "--interactive",
              is_flag=True,
              help="interactive retokenization (with user correction), useless without retokenize", default=False)
@click.option("-p", "--prompt",
              is_flag=True,
              help="prompt the user for the information regarding the speakers instead of using dummy values", default=False)
@click.option("--model", type=click.Path(exists=True, file_okay=False),
              help="path to utterance tokenization model")
def transcribe(ctx, **kwargs):
    """generate and align a CHAT transcript from a media file"""

    # directory retokenization tools
    from .retokenize import retokenize_directory
    # forced alignment tools
    from .fa import do_align

    # ASR
    print("Performing ASR...")
    retokenize_directory(kwargs["in_dir"], model_path=kwargs["model"],
                         interactive=kwargs["interactive"], lang=kwargs["lang"],
                         noprompt=(not kwargs["prompt"]))

    # now, if we need asr, then run ASR
    if kwargs["align"]:
        do_align(kwargs["in_dir"], kwargs["out_dir"], prealigned=True,
                 clean=kwargs["clean"], aggressive=kwargs["aggressive"])
    

#################### MORPHOTAG ################################

@batchalign.command()
@common_options
@click.pass_context
def morphotag(ctx, **kwargs):
    """perform morphosyntactic analysis on a CHAT file"""

    # directory morphosyntactic analysis tools
    from .ud import morphanalyze

    morphanalyze(**kwargs)


#################### BENCHMARK ################################

@batchalign.command()
@common_options
@click.pass_context
@click.option("--beam", type=int,
              default=30, help="beam width for MFA")
@click.option("--model", type=click.Path(exists=True, file_okay=False),
              help="path to utterance tokenization model")
@click.option("--noise", type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help="optional noise profile directory")
def benchmark(ctx, **kwargs):
    """benchmark ASR performance on an existing CHAT file"""

    # benchmarking tools
    from .benchmark import benchmark_directory

    benchmark_directory(kwargs["in_dir"], kwargs["out_dir"],
                        model_path=kwargs["model"], lang=kwargs["lang"],
                        beam=kwargs["beam"], clean=kwargs["clean"], noise=kwargs["noise"])

#################### FEATURIZE ################################

@batchalign.command()
@common_options
@click.pass_context
@click.option("--beam", type=int,
              default=30, help="beam width for MFA")
@click.option("--align/--skipalign",
              help="actually invoke MFA or just run Batchalign operations", default=True)
@click.option("--prealigned/--scratch",
              help="process CHAT file that is already utterance aligned", default=True)
def featurize(ctx, **kwargs):
    """generate .hdf5 feature file usable for analysis"""

    # forced alignment tools
    from .fa import do_align

    # featurization tools
    from .featurize import featurize

    # fa!
    alignments = do_align(**kwargs)

    # featurize
    featurize(alignments, kwargs["in_dir"], kwargs["out_dir"],
              lang=kwargs["lang"], clean=kwargs["clean"])

#################### FEATURIZE ################################

def featurize(ctx, **kwargs):
    """generate .hdf5 feature file usable for analysis"""

    # forced alignment tools
    from .fa import do_align

    # featurization tools
    from .featurize import featurize

    # fa!
    alignments = do_align(**kwargs)

    # featurize
    featurize(alignments, kwargs["in_dir"], kwargs["out_dir"],
              lang=kwargs["lang"], clean=kwargs["clean"])

#################### RECURSIVE ################################

@batchalign.command()
@click.pass_context
@click.argument("in_dir", 
                type=click.Path(exists=True, file_okay=False))
@click.argument("out_dir", 
                type=click.Path(exists=True, file_okay=False))
@click.argument("command", 
                type=str)
def recursive(ctx, **kwargs):
    """batch execute a batchalign command through directories"""

    import os
    import glob
    import shutil
    from pathlib import Path

    # find files and calculate directories
    files = glob.glob(os.path.join(kwargs["in_dir"], '**', '*.*'), recursive=True)
    in_dirs = list(set([os.path.abspath(os.path.join(i, os.pardir)) for i in files]))
    out_dirs = [os.path.abspath(os.path.join(kwargs["out_dir"], os.path.relpath(i, start=kwargs["in_dir"])))
                for i in in_dirs]

    # zip!
    dirs = zip(in_dirs, out_dirs)

    # and now, batchalign for every pair, making directories as needed
    for inp, out in dirs:
        # make out directory
        Path(out).mkdir(parents=True, exist_ok=True)

        # get batchalign
        batchalign_binary = shutil.which("batchalign")

        # batch align!
        os.system(f"{batchalign_binary} {kwargs['command']} {inp} {out}")

#################### SPH/STM Conversion ################################

@batchalign.command(hidden=True)
@click.argument("in_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("out_dir", type=click.Path(exists=True, file_okay=False))
@click.pass_context
def sph(ctx, **kwargs):
    """process sphere files, mostly from TED"""

    # cleanup tools
    from .sph import sph2cha_dir

    sph2cha_dir(kwargs["in_dir"], kwargs["out_dir"])

#################### CLEAN ################################

@batchalign.command()
@common_options
@click.pass_context
def clean(ctx, **kwargs):
    """clean input and output folders"""

    # cleanup tools
    from .utils import cleanup

    click.echo("Performing cleanup operations...")
    cleanup(kwargs["in_dir"], kwargs["out_dir"], "data")

#################### CLEAN ################################

@batchalign.command()
@click.pass_context
def version(ctx, **kwargs):
    """program version info"""

    click.echo()
    click.echo("TalkBank Batchalign")
    click.echo(f"-------------------")
    click.echo("Developed by Brian MacWhinney and Houjun Liu")
    click.echo(f"Version v{VERSION}")
    click.echo(f"--------------------------------------------")
    click.echo(f"{NOTES}")
    click.echo()
   
