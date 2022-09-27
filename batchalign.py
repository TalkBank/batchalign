# batchalign.py
# batch alignment tool for chat files and transcripts
#
## INSTALLING CLAN ##
# a full UnixCLAN suite of binaries is placed in ./opt/clan
# For instance, the file ./opt/clan/praat2chat should exist
# and should be executable.
#
## INSTALLING MFA ##
# MFA should be present on the system.
# conda config --add channels conda-forge
# conda install montreal-forced-aligner
# conda install pynini
#
## INSTALLING FFMPEG ##
# the penn aligner only aligns wav files. Therefore, we use
# ffmpeg to convert mp3 to wav
#
# Of course, this can be changed if needed.

from baln.command_line import mainloop

if __name__=="__main__":
    mainloop()
