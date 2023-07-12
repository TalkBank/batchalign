# import os
import os


# silence huggingface
os.environ["TOKENIZERS_PARALLELISM"] = "FALSE"


# progra freezing utilities
from multiprocessing import Process, freeze_support

# import argparse
import argparse



# wrap everything in a mainloop for multiprocessing guard
def cli():
    # get mode from command line flag
    mode = os.environ.get("BA_MODE")
    MODE = -1

    REV_API = os.environ.get("REV_API")

    if mode == "+Analyze Raw Audio+":
        MODE = 1
    elif mode == "+Analyze Rev.AI Output+":
        MODE = 1
    elif mode == "+Realign CHAT+":
        MODE = 0

    # manloop to take input
    parser = argparse.ArgumentParser(description="batch align .cha to audio in a directory with MFA")
    parser.add_argument("in_dir", type=str, help='input directory containing .cha and .mp3/.wav files')
    parser.add_argument("out_dir", type=str, help='output directory to store aligned .cha files')
    parser.add_argument("--prealigned", default=False, action='store_true', help='input .cha has utterance-level alignments')
    parser.add_argument("--aggressive", default=False, action='store_true', help='use dynamic programming to aggressively align the audio')
    parser.add_argument("--data_dir", type=str, default="data", help='subdirectory of out_dir to use as data dir')
    parser.add_argument("--beam", type=int, default=30, help='beam width for MFA, ignored for P2FA')
    parser.add_argument("--skipalign", default=False, action='store_true', help='don\'t align, just call CHAT ops')
    parser.add_argument("--skipclean", default=False, action='store_true', help='don\'t clean')
    parser.add_argument("--dictionary", type=str, help='path to custom dictionary')
    parser.add_argument("--model", type=str, help='path to custom model')
    parser.add_argument("--retokenize", type=str, help='retokenize input with model')
    parser.add_argument('-i', "--interactive", default=False, action='store_true', help='interactive retokenization (with user correction), useless without retokenize')
    parser.add_argument('-n', "--headless", default=False, action='store_true', help='interactive without GUI prompt, useless without -i')
    parser.add_argument('-a', "--asronly", default=False, action='store_true', help='ASR only, don\'t run mfa')
    parser.add_argument("--rev", type=str, help='rev.ai API key, to submit audio')
    parser.add_argument("--clean", default=False, action='store_true', help='don\'t align, just call cleanup')

    return MODE, REV_API, parser.parse_args()

def mainloop():
    # import our utilities
    # directory retokenization tools
    from .retokenize import retokenize_directory
    # directory forced alignment tools 
    from .fa import do_align
    # utilities
    from .utils import cleanup, globase

    # code freezing helper
    freeze_support()

    # parse!
    MODE, REV_API, args = cli()

    # print(args.beam)
    # breakpoint()

    # if we are cleaning
    if args.clean:
        cleanup(args.in_dir, args.out_dir, args.data_dir)
        # if we need to retokenize or run with audio only (i.e. no files avaliable)
    elif (args.retokenize and MODE != 0) or ((len(globase(args.in_dir, "*.cha")) == 0) and
                                             (len(globase(args.in_dir, "*.json")) == 0)) or MODE == 1:
        # assert retokenize
        # assert args.retokenize, "Only audio files provided, but no segmentation model provided with --retokenize!"
        # assert retokenize
        print("Stage 1: Performing ASR")
        retokenize_directory(args.in_dir, args.retokenize if args.retokenize else "~/mfa_data/model", 'h' if args.headless else args.interactive, args.rev)
        if not args.asronly:
            print("Stage 2: Performing Forced Alignment")
            do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=True, beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.model, aggressive=args.aggressive)
        else:
            # Define the data_dir
            DATA_DIR = os.path.join(args.out_dir, args.data_dir)

            # Make the data directory if needed
            if not os.path.exists(DATA_DIR):
                os.mkdir(DATA_DIR)

            # cleanup
            cleanup(args.in_dir, args.out_dir, args.data_dir)
            print("All done! Check the output folder.")
            # otherwise prealign
    else: 
        print("Stage 1: Performing Forced Alignment")
        do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=(True if MODE==0 else args.prealigned), beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.model, aggressive=args.aggressive)
        print("All done! Check the output folder.")