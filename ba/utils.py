# import os utilties
import os
# and glob
import glob
# pathlib
import pathlib

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)

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

