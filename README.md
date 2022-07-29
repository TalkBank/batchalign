# batchalign
`batchalign` is a Python script that uses the Montreal Forced Aligner and the Unix version of CLAN to batch-align data in TalkBank.

# Setup and Usage 

## Setup

Begin by setting up a machine with a default package manager. For macOS (M1 or otherwise) this means setting up Homebrew with instrucitons at https://brew.sh/.

Acquire also a copy of UnixCLAN from https://dali.talkbank.org/clan/unix-clan.zip. Its `0readme.txt` should contain its own setup instructions. Remember to set the shell `PATH` variable to ensure that the UnixCLAN suite can be called.

Then, install anaconda, the environment tool:

```bash
brew install miniforge ffmpeg
```

Finally, create an environment called aligner with the required dependencies:

```bash
conda create -n aligner montreal-forced-aligner pynini
```

## Typical Usage

Activate the alignment environment:

```bash
conda activate aligner
```

Ok. You are now ready to run MFA. Begin by placing .cha and .wav/.mp3 to align together in your input folder. For instance, `~/mfa_data/input`. Create also an empty folder at `~/mfa_data/output`, which will contain the output of MFA.

The input folder has to be organized in a very specific way. Inside it, place ONLY `.cha` files and `.mp3` or `.wav` files to align with the `.cha` files with the same name. 

Therefore, a successful placement of the input folder would look like

ls ~/mfa_data/input

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

The following line also assumes that the batchalign script is located at `~/mfa_data/batchalign-dist/batchalign.py`.

To align, execute:

```bash
python ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output
```

The resulting aligned files will be located at ~/mfa_data/output.

# Other Commands

## Align with existing TextGrid files

This command assumes, in to addition to `~/mfa_data/input`, that there is a `data/` subfolder in `~/mfa_data/output` which contains already-aligned TextGrid files.

```bash
python ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output --skipalign
```

## Align with existing dictionary

This command assumes, in to addition to `~/mfa_data/input`, there is a dictionary located at `~/mfa_data/dictionary.dict`.

```bash
python ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output --dictionary ~/mfa_data/dictionary.dict
```

## Process Rev.AI JSON

`batchalign` has also the ability to handle the output of ASR (and, hopefully in the future, interface with the ASR API). This functionality assumes that you have already performed ASR on your audio.

This command assumes, in to addition to `~/mfa_data/input`, there is a dictionary located at `~/mfa_data/dictionary.dict`, as well as a trained tokenization model located at `~/mfa_data/model/`.


```bash
python ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output --retokenize ~/mfa_data/model
```

There is additionally a `-i` flag that allows interactive tokenization fixes. 

```bash
python ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output --retokenize ~/mfa_data/model -i
```

Follow the on-screen prompts for details and next steps.

## Clean up
If there is stray files in the input folder (`.eaf`, `.lab`, etc.) after alignment, it is likely that the program crashed. To clean up all stray files, run:

```bash
python3 ~/mfa_data/batchalign-dist/batchalign.py ~/mfa_data/input ~/mfa_data/output --clean
```

# Full Usage Documentation 

```
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
```
