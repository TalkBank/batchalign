# import os utilties
import os
# and glob
import glob
# pathlib
import pathlib
# regular expressions
import re


# resolve CLAN
def resolve_clan():
    # resolve for where CLAN is
    if os.path.isfile("./flo"):
        return "."
    else:
        return ""

CLAN_PATH=resolve_clan()

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)

def strip_bullets(f):
    """Remove bullets from a file

    Attributes:
        f (string): file path

    Returns:
        none, used for side effects
    """

    # get abspath of file
    f = os.path.abspath(f)
    # open the file and strip bullets
    with open(f, 'r') as df:
        file_content = df.read()
        # remove all bullet symbols
        new_string = re.sub(r'\d+_\d+', '', file_content)
    # open the file and write content
    with open(f, 'w') as df:
        # write
        df.write(new_string)

def change_media(f, format="video"):
    """Change the media header to say a different format

    Attributes:
        f (string): file path

    Returns:
        none, used for side effects
    """

    # get abspath of file
    f = os.path.abspath(f)
    # open the file and strip bullets
    with open(f, 'r') as df:
        file_content = df.read()
        # remove all bullet symbols
        new_string = re.sub(r'@Media:(.*), .*', r"@Media:\1, "+format, file_content)
    # open the file and write content
    with open(f, 'w') as df:
        # write
        df.write(new_string)

def fix_transcript(f):
    """Fix transcript by adding any needed annotations, retracings, etc.

    Attributes:
        f (string): file path

    Returns:
        none, used for side effects
    """

    # get dir
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # get abspath of file
    f = os.path.abspath(f)

    ###########################################
    ## Fix disfluencies and join group words ##
    ###########################################

    DISFLUENCY_FILE = os.path.abspath(os.path.join(dir_path, "disfluencies.cut"))
    REP_JOIN_FILE = os.path.abspath(os.path.join(dir_path, "rep-join.cut"))
    # run disfluency replacement
    CMD = f"{os.path.join(CLAN_PATH, 'chstring')} +c{DISFLUENCY_FILE} {f} "
    os.system(CMD)
    # move old file to backup
    os.rename(f, f.replace("cha", "old.cha"))
    # rename new file
    os.rename(f.replace("cha", "chstr.cex"), f)
    # run rep join replacement
    CMD = f"{os.path.join(CLAN_PATH, 'chstring')} +c{REP_JOIN_FILE} {f} "
    os.system(CMD)
    # delete old file
    os.remove(f)
    # rename new file
    os.rename(f.replace("cha", "chstr.cex"), f)


    ###############
    ## Retracing ##
    ###############

    # run 
    CMD = f"retrace +c {f} "
    os.system(CMD)
    # delete old file
    os.remove(f)
    # rename new file
    os.rename(f.replace("cha", "retrace.cex"), f)


    #################
    ## Lowercasing ##
    #################

    CAPS_FILE = os.path.abspath(os.path.join(dir_path, "caps.cut"))
    # save/change workdir for lowcase
    workdir = os.getcwd()
    # change it to the output
    os.chdir(pathlib.Path(f).parent.absolute())
    # run 
    CMD = f"lowcase +d1 +i{CAPS_FILE} {os.path.basename(f)} "
    os.system(CMD)
    # change it back to the output
    os.chdir(workdir)
    # delete old file
    os.remove(f)
    # rename new file
    os.rename(f.replace("cha", "lowcas.cex"), f)

def cleanup(in_directory, out_directory, data_directory="data"):
    """Clean up alignment results so that workspace is clear

    Attributes:
        in_directory (string): the input directory containing files
        out_directory (string): the output directory containing possible output files
        data_directory (string): a subdirectory which the misc. outputs go

    Returns:
        none
    """

    # Define the data_dir
    DATA_DIR = os.path.join(out_directory, data_directory)

    # move all the lab files 
    tgfiles = globase(in_directory, "*.textGrid")
    # Rename each one
    for f in tgfiles:
        # we don't actually want to repath UPPERCASE TextGrid
        # unfortunately windows is not smart enough to ignore
        # it in the glob.
        if "TextGrid" in f:
            continue
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the lab files 
    tgfiles = globase(in_directory, "*.TextGrid")
    # Rename each one
    for f in tgfiles:
        os.rename(f, repath_file(f.replace("TextGrid", "orig.textGrid"), DATA_DIR)) 

    # move all the lab files 
    labfiles = globase(in_directory, "*.lab")
    # Rename each one
    for f in labfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the wav files 
    wavfiles = globase(in_directory, "*.orig.wav")
    # Rename each one
    for f in wavfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the rest of wav files 
    mp3files = globase(in_directory, "*.mp3")
    # Rename each one
    for f in mp3files:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the rest of mp4 files 
    mp4files = globase(in_directory, "*.mp4")
    # Rename each one
    for f in mp4files:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the orig.cha files from repathing
    chafiles = globase(in_directory, "*.orig.cha")
    # Rename each one
    for f in chafiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # move all the old.cha files from repathing
    chafiles = globase(in_directory, "*.old.cha")
    # Rename each one
    for f in chafiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # delete all the old.cha files from output
    chafiles = globase(out_directory, "*.old.cha")
    # Rename each one
    for f in chafiles:
        os.rename(f, repath_file(f, DATA_DIR).replace(".old.cha", ".unfix.cha")) 

    # clean up the elans
    elanfiles = globase(out_directory, "*.eaf")
    # Rename each one
    for f in elanfiles:
        os.rename(f, repath_file(f, DATA_DIR)) 

    # Clean up the dictionary, if exists
    dict_path = os.path.join(in_directory, "dictionary.txt")
    # Move it to the data dir too
    if os.path.exists(dict_path):
        os.rename(dict_path, repath_file(dict_path, DATA_DIR))

    # Cleaning up
    # Removing all the eaf files generated
    for eaf_file in globase(in_directory, "*.eaf"):
        os.remove(eaf_file)
    for eaf_file in globase(out_directory, "*.eaf"):
        os.remove(eaf_file)

    # Removing all the transcript files generated
    for eaf_file in globase(in_directory, "*.txt"):
        os.remove(eaf_file)

# fixbullets a whole path
def fixbullets(directory):
    """Fix a whole folder's bullets

    files:
        directory (string): the string directory in which .chas are in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # process each file
    for fl in files:
        # elan2chatit!
        CMD = f"{os.path.join(CLAN_PATH, 'fixbullets ')} {fl} "
        # run!
        os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # delete any preexisting chat files to old
    for f in globase(directory, "*.cha"):
        os.rename(f, f.replace("cha", "old.cha"))
    # and rename the files
    for f in globase(directory, "*.fxblts.cex"):
        os.rename(f, f.replace(".fxblts.cex", ".cha"))

# chat2transcript a whole path
def chat2transcript(directory, mor=False):
    """Generate transcripts for a whole directory

    Arguments:
        directory (string): string directory filled with chat files
        mor (bool): generate mor-like output

    Returns:
        none
    """

    # then, finding all the cha files
    files = globase(directory, "*.cha")

    # use flo to convert chat files to text
    if mor:
        CMD = f"{os.path.join(CLAN_PATH, 'flo +d +cm +t*')} {' '.join(files)} "
    else:
        CMD = f"{os.path.join(CLAN_PATH, 'flo +d +ca +t*')} {' '.join(files)} "

    # run!
    os.system(CMD)

    # and rename the files to lab files, which are essentially the same thing
    for f in globase(directory, "*.flo.cex"):
        os.rename(f, f.replace(".flo.cex", ".lab"))


# chat2praat, then clean up tiers, for a whole path
def chat2praat(directory):
    """Convert a whole directory to praat files

    Arguments:
        directory (string) : string directory filled with chat

    Returns:
        none
    """
    # then, finding all the cha files
    files = globase(directory, "*.cha")

    # use flo to convert chat files to text
    CMD = f"{os.path.join(CLAN_PATH, 'chat2praat +e.wav +c -t% -t@')} {' '.join(files)} "
    # run!
    os.system(CMD)

    # then, finding all the praat files
    praats = globase(directory, "*.c2praat.textGrid")

    for praat in praats:
        # load the textgrid
       os.rename(praat, praat.replace("c2praat.textGrid", "TextGrid"))

    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)


# optionally convert mp3 to wav files
def mp32wav(directory):
    """Generate wav files from mp3

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    mp3s = globase(directory, "*.mp3")

    # convert each file
    for f in mp3s:
        os.system(f"ffmpeg -i {f} {f.replace('mp3','wav')} -c copy")

# optionally convert mp4 to wav files
def mp42wav(directory):
    """Generate wav files from mp4

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    mp4s = globase(directory, "*.mp4")

    # convert each file
    for f in mp4s:
        os.system(f"ffmpeg -i {f} {f.replace('mp4','wav')} -c copy")

def wavconformation(directory):
    """Reconform wav files

    Arguments:
        directory (string): string directory filled with chat files

    Returns:
        none
    """

    # then, finding all the elan files
    wavs = globase(directory, "*.wav")

    # convert each file
    for f in wavs:
        # Conforming the wav
        os.system(f"ffmpeg -i {f} temp.wav")
        # move the original
        os.remove(f)
        # and move the new back
        os.rename("temp.wav", f)
