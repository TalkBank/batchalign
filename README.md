# batchalign

[![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/version.svg)](https://anaconda.org/talkbank/batchalign) [![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/latest_release_date.svg)](https://anaconda.org/talkbank/batchalign) [![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/platforms.svg)](https://anaconda.org/talkbank/batchalign)

`batchalign` is a Python script that uses the Montreal Forced Aligner and the Unix version of CLAN to batch-align data in TalkBank.

The following guide provides a very rough overview of the primary functionality of `batchalign`, and assumes basic familarity with POSIX-like systems and their operations. If needed, [visit this guide](https://talkbank.org/info/batchalign.docx) for more detailed instructions.

# Setup and Usage 

`batchalign` is available through the `TalkBank` channel in Miniconda. To get started, begin by [installing anaconda](https://www.anaconda.com/products/distribution). Windows users only before `Windows 10 1809` (September, 2018) will also need to [install curl via these instructions](https://developer.zendesk.com/documentation/developer-tools/getting-started/installing-and-using-curl/#installing-curl). For the rest of the guide, we will be assuming the usage of your default command prompt with a working Miniconda installation.

The final screen of the Conda installer will usually describe the next steps for Conda configuration; this final step may often involve, *in the same shell*, running

```bash
conda init
```
to initialize Anaconda for your workspace.

For macOS and Linux users needing to perform this step manually (i.e. the final screen of the installer didn't offer to do it automatically or provide next step instructions), the process will involve executing some variant of the commands `source [PATH TO WHERE CONDA IS INSTALLED]/bin/activate` and `conda init`. 

## First Time Setup
If you have never used `batchalign` before, execute the following (remember to hover your cursor over the following codeblock, and tap the copy button that appears to the right to ensure you copy the whole command)

```bash
curl -O "https://raw.githubusercontent.com/TalkBank/batchalign/master/environment.yml" & conda env create -f environment.yml
```

This will create an environment named `batchalign` following our preselected settings, which we will enable in your terminal each time.

## Using batchalign
Before any of the following commands apply, we first have to enable the `batchalign` environment we created above.

```bash
conda activate batchalign
```

You are now ready to run `batchalign`. Begin by placing .cha (if present with "utterance-level bullets") and .wav/.mp3/.mp4 to align together in your input folder. For instance, `~/mfa_data/input`. Create also an empty folder at `~/mfa_data/output`, which will contain the output of MFA.

The input folder has to be organized in a very specific way. Inside it, place ONLY `.mp3`, `.mp4`, or `.wav` files and---if needed and available---CHAT files with utterance-level prealignments to align with the `.cha` files with the same name. Do not mix input media types: the folder should contain only one type of media file.

The output folder should be empty.

### Process Raw Audio Files
`batchalign` has the ability to handle pure audio files by calling the ASR facilities of [rev.ai](https://www.rev.ai/). This functionality assumes that you already have an API key to `Rev.AI`. This key should be a string with a large series of numbers.

If this is the first time you are running this command, we will prompt for you `Rev.AI` API key. After you enter it once, it will be stored in `~/mfa_data/rev_key` as a text file. We will also download a copy of our pretrained NER model, if not already present, and store it in `~/mfa_data/model`.

```bash
batchalign ~/mfa_data/input ~/mfa_data/output 
```

To use the interactive prompt facility available for the user to easily fix segmentation results, add the `-i` flag to the end of the command. 

```bash
batchalign ~/mfa_data/input ~/mfa_data/output -i
```

and follow on screen instructions to correct the automated segmentation.

Note that, regardless of whether or not the `-i` flag was selected, we will always prompt with interactive on-terminal instructions for speaker assignment to allow the user to quickly identify and label each distinct speaker identified in the text. 

### Align with Existing Utterance-Level Alignments
This form assumes that there is already utterance-level alignments ("bullets") inside the `.cha` files placed in `~/mfa_data/input`. If not, please use the "Audio/Transcript Alignment" (triggered with key "F5") functionality in CLAN to preliminary annotate utterance alignments to use the raw audio files functionality above to get started fresh.

To align with existing utterance bullets, execute:

```bash
batchalign ~/mfa_data/input ~/mfa_data/output --prealigned
```

The resulting aligned files will be located at `~/mfa_data/output`.

## Update batchalign
We can use conda to update `batchalign`, in much of a similar way as installing it.

First, start by activating `batchalign`.

```bash
conda activate batchalign
```

Then, run the following command to check and perform updates

```bash
conda update batchalign -c talkbank
```

## Uninstall batchalign
To uninstall `batchalign`, first ensure that you are not inside the `batchalign` environment. To check this, ensure that the command line says `(base)` instead of `(batchalign)`. If not, run:

```bash
conda deactivate
```

Then, we will remove the environment:

```bash
conda env remove -n batchalign
```

## Rebuild batchalign
If your environment is irreparably broken (i.e. complex dependency mismatches, weird linker errors, etc.), it is probably an easy troubleshoot step to rebuild batchalign. To do this, follow the instructions to

1. Uninstall batchalign
2. Install batchalign

# Other Commands

## Align with existing TextGrid files

This command assumes, in to addition to `~/mfa_data/input`, that there is a `data/` subfolder in `~/mfa_data/output` which contains already-aligned TextGrid files. We therefore don't actually run MFA, instead, we just run the postprocessing and code-generation facilities.

```bash
batchalign ~/mfa_data/input ~/mfa_data/output --skipalign
```

## Align with existing dictionary

This command assumes, in to addition to `~/mfa_data/input`, there is a dictionary located at `~/mfa_data/dictionary.dict`.

```bash
batchalign ~/mfa_data/input ~/mfa_data/output --dictionary ~/mfa_data/dictionary.dict
```

## Clean up
If there is stray files in the input folder (`.eaf`, `.lab`, etc.) after alignment, it is likely that the program crashed. To clean up all stray files, run:

```bash
batchalign ~/mfa_data/input ~/mfa_data/output --clean
```

# Full Command Documentation 

```
Usage: batchalign.py [OPTIONS] COMMAND [ARGS]...

  batch process CHAT files in IN_DIR and dumps them to OUT_DIR

Options:
  --help  Show this message and exit.

Commands:
  align       align a CHAT transcript against a media file
  clean       clean input and output folders
  featurize   generate .hdf5 feature file usable for analysis
  morphotag   perform morphosyntactic analysis on a CHAT file
  transcribe  generate and align a CHAT transcript from a media file
  version     program version info
```
