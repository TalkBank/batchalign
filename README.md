# batchalign

[![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/version.svg)](https://anaconda.org/talkbank/batchalign) [![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/latest_release_date.svg)](https://anaconda.org/talkbank/batchalign) [![Anaconda-Server Badge](https://anaconda.org/talkbank/batchalign/badges/platforms.svg)](https://anaconda.org/talkbank/batchalign)

Hello! Welcome to the Batchalign repository. `batchalign` is a Python script that uses the Montreal Forced Aligner and the Unix version of CLAN to batch-align data in TalkBank.

**For most users, we recommend you [visit this detailed guide](https://talkbank.org/info/batchalign.docx) for more detailed instructions.** The remaining instructions on this page provides a very rough overview of the primary functionality of `batchalign`, and assumes familiarity with Docker, Anaconda, and Python. 

Note that, as Batchalign depends on specific platform-specific C programs in the CLAN suite to process CHAT files, Microsoft Windows is currently not supported natively. **Please follow the Docker installation instructions below to use Batchalign on Windows**.

## Overview
There are three main interfaces to using Batchalign:

1. **Docker + Web User Interface**: simple to setup, easy to use, covers most basic functionality
2. **Anaconda Based CLI Program**: covers all options and functionalities of Batchalign, requires extensive Terminal use
3. **Python API**: used to embed Batchalign in other programs

Select the flavour which you would like to use, and proceed with the relevant section of instructions below.

## Docker
The quick start instructions for the Docker + Web setup is available separately by [tapping on this link](https://github.com/TalkBank/batchalign-docker). 

## Anaconda
The `batchalign` package is available though the `talkbank` channel on Anaconda. It requires dependencies on `conda-forge` as well as `rev_ai` from `pip`. Hence, to quickly setup batchalign:

```bash
conda create -n batchalign
conda activate batchalign
conda install batchalign -c talkbank -c conda-forge
pip install rev_ai
```

Then, the `batchalign` environment should have the program installed. 

The CLI program is used in the following basic way:

```
batchalign [verb] [input_dir] [output_dir]
```

Where `verb` includes:

1. `transcribe` - placing only an audio of video file (`.mp3/.mp4/.wav`) in the input directory, perform ASR on the audio, diarizes utterances, identifies some basic conversational features like retracing and filled pauses, and generate word-level alignments
2. `align` - placing both an audio of video file (`.mp3/.mp4/.wav`) and an *utterance-aligned* CHAT file in the input directory, generate word-level alignments
3. `morphotag` - placing a CHAT file in the input directory, uses Stanford NLP Stanza to generate morphological and dependency analyses; note that the flag `--lang=[two letter ISO language code]`, like `--lang=en` is needed to tell Stanza what language we are working with

Follow instructions from

```
batchalign --help
```

and 

```
batchalign [verb] --help
```

to learn more about other options.

## Programmatic
Coming soon. The package is called `baln`. After following the instructions from the "Anaconda" setup section above, one can import APIs that perform the same actions as the CLI tool along some even more advanced custom analysis.
