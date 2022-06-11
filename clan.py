# clan.py
# CLAN helper facilities; this script assumes that
# a full UnixCLAN suite of binaries is placed in ./opt/clan
#
# For instance, the file ./opt/clan/praat2chat should exist
# and should be executable.
#
# Of course, this can be changed if needed.

# Pathing facilities
import pathlib

# I/O and stl
import os

# Import pathing utilities
import glob

# Oneliner of directory-based glob
globase = lambda path, statement: glob.glob(os.path.join(path, statement))

# Get the default path of UnitCLAN installation
# from the path of the current file
CURRENT_PATH=pathlib.Path(__file__).parent.resolve()
CLAN_PATH=os.path.join(CURRENT_PATH, "./opt/clan")

# chat2praat a whole path
def chat2praat(directory):
    """Convert a folder of CLAN .cha files to corresponding textGrid files

    Attributes:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # praat2chatit!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2praat')} +e.wav {' '.join(files)}"
    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.textGrid"):
        os.rename(f, f.replace(".c2praat", ""))

# chat2elan a whole path
def chat2elan(directory):
    """Convert a folder of CLAN .cha files to corresponding ELAN XMLs

    files:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # praat2chatit!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2elan')} +e.wav {' '.join(files)}"
    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.eaf"):
        os.rename(f, f.replace(".c2elan", ""))
