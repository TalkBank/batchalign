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
    # manloop to take input
    parser = argparse.ArgumentParser(description="CHAT transcript batch-processing utilities")

    # seperate commands
    subparsers = parser.add_subparsers(dest="command")

    #### subparsers ####
    # .wav => .cha full generation commands
    generate = subparsers.add_parser("generate")
    generate.add_argument('-i', "--interactive", default=False, action='store_true', help='interactive retokenization (with user correction), useless without retokenize')
    generate.add_argument('-n', "--headless", default=False, action='store_true', help='interactive without GUI prompt, useless without -i')
    generate.add_argument('-a', "--asronly", default=False, action='store_true', help='ASR only, don\'t run mfa')
    generate.add_argument("--utterancemodel", type=str, help='path to utterance tokenization model')
    generate.add_argument("--rev", type=str, help='rev.ai API key, to submit audio')

    # .wav + .cha => .cha %wor alignment commands
    alignment = subparsers.add_parser("align")
    alignment.add_argument("--beam", type=int, default=30, help='beam width for MFA, ignored for P2FA')
    alignment.add_argument("--skipalign", default=False, action='store_true', help='don\'t align, just call CHAT ops')
    alignment.add_argument("--fromscratch", default=False, action='store_true', help='input .cha has utterance-level alignments')

    # cleanup commands
    clean = subparsers.add_parser("clean")

    #### master commands ####
    parser.add_argument("in_dir", type=str, help='input directory containing .cha and .mp3/.wav files')
    parser.add_argument("out_dir", type=str, help='output directory to store aligned .cha files')
    parser.add_argument("--data_dir", type=str, default="data", help='subdirectory of out_dir to use as data dir')
    parser.add_argument("--skipclean", default=False, action='store_true', help='don\'t clean')
    parser.add_argument("--dictionary", type=str, help='path to custom dictionary')
    parser.add_argument("--alignmentmodel", type=str, help='path to custom kaldi alignmetn model')

    return parser.parse_args()

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
    args = cli()

    # if we are cleaning
    if args.command =="clean":
        print("Stage 1: Cleaning Folders")
        cleanup(args.in_dir, args.out_dir, args.data_dir)
        print("All done! Check the input folder.")
        # if we need to retokenize or run with audio only (i.e. no files avaliable)
    elif args.command =="generate":
        # assert retokenize
        print("Stage 1: Performing ASR")
        retokenize_directory(args.in_dir, args.utterancemodel if args.utterancemodel else "~/mfa_data/model", 'h' if args.headless else args.interactive, args.rev)
        if not args.asronly:
            print("Stage 2: Performing Forced Alignment")
            do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=True, beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.alignmentmodel)
        else:
            # Define the data_dir
            DATA_DIR = os.path.join(args.out_dir, args.data_dir)

            # Make the data directory if needed
            if not os.path.exists(DATA_DIR):
                os.mkdir(DATA_DIR)

            # cleanup
            cleanup(args.in_dir, args.out_dir, args.data_dir)
        print("All done! Check the input folder.")
    elif args.command == "align": 
        print("Stage 1: Performing Forced Alignment")
        do_align(args.in_dir, args.out_dir, args.data_dir, prealigned=(not args.fromscratch), beam=args.beam, align=(not args.skipalign), clean=(not args.skipclean), dictionary=args.dictionary, model=args.alignmentmodel)
        print("All done! Check the input folder.")
    else:
        raise Exception("Unknown command passed to parser!")
