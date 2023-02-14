import click
import functools

from multiprocessing import Process, freeze_support

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
                     help="sample language in two-letter code",
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

@batchalign.result_callback()
def process_result(result, **kwargs):
    click.echo("Done! Check the output folder.")

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
                         interactive=kwargs["interactive"], lang=["lang"])

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

