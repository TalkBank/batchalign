batchalign is a Python script that uses the Penn Phonetics Forced Aligner and the Unix version of CLAN to batch-align data in TalkBank.

=== Software Installation ===

  == HTK ==

  Download HTK (https://htk.eng.cam.ac.uk/ftp/software/HTK-3.5.beta-2.tar.gz).
    HTK version 3.5.1 doesn't always play nice with p2fa. We provided
    here in this folder a patch to install it on macOS.

    Hence, download HTK. Deflate it, then, in the working directory of the
    HTK source type "git apply < THIS_FOLDER/htk.patch".

    Finally, compile and install HTK Binaries. HVite, for instance, should
    be callable.

  == UnixCLAN ==

    Download UnixCLAN (https://dali.talkbank.org/clan/unix-clan.zip). Follow
    its instructions for installation. chat2praat, for instance, should be
    callable.


  == ffmpeg ==

    ffmpeg is used for audio conversion. Download it using your package manager

=== Running ===

This program comes with a copy of P2FA and the requisite models. Therefore, it
can be simply ran as a Python script.

The input folder has to be organized in a very specific way. Inside it, place ONLY
=.cha= files and =.mp3= or =.wav= files to align with the =.cha= files with the same
name.

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

  The input folder will briefly populate with some supplemental files, before
  begin aligned. Aligned .cha files will be in the output directory specified,
  whereas aligned .textGrid (compressed form) will be in the original input
  folder.

