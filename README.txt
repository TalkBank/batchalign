batchalign is a Python script that uses the Montreal Forced Aligner OR Penn Phonetics Forced Aligner and the Unix version of CLAN to batch-align data in TalkBank.

=== Quick Setup and Usage ===

## Setup

Begin by setting up a machine with a default package manager. For macOS (M1 or otherwise)
this means setting up Homebrew (https://brew.sh/).

Then, install anaconda, the environment tool:

brew install miniforge

Then, create an environment called aligner with the required dependencies:

conda create -n aligner montreal-forced-aligner pynini

## Usage

Activate this environment:

conda activate aligner

Ok. You are now ready to run MFA. Begin by placing .cha and .wav/.mp3 to align together
in your input folder. For instance, ~/mfa_data/input. Create also an empty folder at
~/mfa_data/output, which will contain the output of MFA.

The following line also assumes that the batchalign script is located at
~/mfa_data/batchalign-dist/batchalign.py.

To align, execute:

python3 ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output

The resulting aligned files will be located at ~/mfa_data/output.

=== Detailed Installation Instructions===

  == For MFA: Download MFA ==

    Install anaconda
    (https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

    Then, type the following commands
    conda config --add channels conda-forge
    conda install montreal-forced-aligner
    conda install pynini

  == UnixCLAN ==

    Download UnixCLAN (https://dali.talkbank.org/clan/unix-clan.zip).
    Follow its instructions for installation. chat2praat, for instance,
    should be callable.

  == ffmpeg ==

    ffmpeg is used for audio conversion. Download it using your package
    manager.

=== Running ===

This program comes with a copy of P2FA and the requisite models.
Therefore, it can be simply run as a Python script.

The input folder has to be organized in a very specific way. Inside
it, place ONLY =.cha= files and =.mp3= or =.wav= files to align with
the =.cha= files with the same name.

  Therefore, a successful placement of the input folder would look like

  ls input/

    413.cha 572.wav 727.cha 871.cha
    413.wav 573.cha 727.wav 871.wav
    420.cha 573.wav 729.cha 872.cha
    420.wav 574.cha 729.wav 872.wav
    427.cha 574.wav 731.cha 874.cha
    427.wav 575.cha 731.wav 874.wav
    444.cha 576.cha 733.cha 875.cha
    444.wav 576.wav 733.wav 875.wav
    474.cha 607.cha 735.cha 877.cha

The output folder should be empty.

Finally, to generate aligned .textGrid and .cha files, simply execute

python3 batchalign.py input_folder empty_output_folder

The input folder will briefly populate with some supplemental files,
before begining to be aligned. Aligned .cha files will be in the
output directory specified, whereas aligned .textGrid, .lab
transcripts, and generated .wav files will be in a subfolder
named "data" in the output directory.

=== Usage Example ===

Here's a typical usage example of the program. The following documentation
all assumes that a copy of batchalign is placed in
~/mfa_data/batchalign-dist/batchalign.py, a directory of .cha and .wav files
in ~/mfa_data/my_corpus, and an empty folder in ~/mfa_data/my_corpus_aligned

## Common Setup
Set up the Montreal forced aligner at
(https://montreal-forced-aligner.readthedocs.io/en/latest/installation.html) as
well as download and install the latest version of UnixClan located online at
(https://dali.talkbank.org/clan/unix-clan.zip).

Then, if needed

conda activate aligner

## Aligning Files

python3 ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/my_corpus ~/mfa_data/my_corpus_aligned

## Align with existing TextGrid files

This command assumes, in to addition to ~/mfa_data/my_corpus_aligned,
that there is a data/ subfolder in ~/mfa_data/my_corpus_aligned which
contains already-aligned TextGrid files.

python3 ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/my_corpus ~/mfa_data/my_corpus_aligned --skipalign

## Clean up
If there is stray files in the input folder after alignment, it is
likely that the program crashed. To clean up all stray files,
run:

python3 ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/my_corpus ~/mfa_data/my_corpus_aligned --clean

=== Usage Documentation ===

usage: batchalign.py [-h] [--data_dir DATA_DIR] [--beam BEAM] [--skipalign]
                     [--clean]
                     in_dir out_dir

batch align .cha to audio in a directory with MFA/P2FA

positional arguments:
  in_dir               input directory containing .cha and .mp3/.wav files
  out_dir              output directory to store aligned .cha files

optional arguments:
  -h, --help           show this help message and exit
  --data_dir DATA_DIR  subdirectory of out_dir to use as data dir
  --beam BEAM          beam width for MFA, ignored for P2FA
  --skipalign          don't align, just call CHAT ops
  --clean              don't align, just call cleanup
