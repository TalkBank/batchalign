# XML facilities
import xml.etree.ElementTree as ET

# Also, stdlib
import re, os

# glob
import glob

# import cleanup
from .utils import resolve_clan

CLAN_PATH=resolve_clan()

# Oneliner of directory-based glob and replace
globase = lambda path, statement: glob.glob(os.path.join(path, statement))
repath_file = lambda file_path, new_dir: os.path.join(new_dir, pathlib.Path(file_path).name)
bullet = lambda start,end: f" {int(round(start*1000))}_{int(round(end*1000))}" # start and end should be float seconds

# indent an XML
def indent(elem, level=0):
    """Indent an XML

    Attributes:
        element (ET.ElementTree.root): element tree root
        level (int): which level to start aligning from

    Citation:
    https://stackoverflow.com/a/33956544/5684313

    Returns void
    """

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def eafalign(root, annotations, alignments):
    """inject MFA alignments into EAF (%wor tier)

    Attributes:
        root (ET.ElementTree): element tree
        annotations (tuple(time, TIER, id)): tier information extracted from input
        alignments (dict): raw, processed MFA output dictionary from fa.transcript*()

    Returns:
        None

    Side effects:
        Modify root
    """

    # get the tiers
    tiers = root[2:]

    # create a lookup dict of xwor tier outputs
    terms_flattened = list(zip([i[-1] for i in annotations], alignments["terms"]))
    terms_dict = dict(terms_flattened)

    # set alignment back to what the rest of the function would expect
    alignments = alignments["alignments"]

    # Create the xword annotation ID index
    id_indx = 0

    # replace content with the bulleted version
    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # create new xword tier
        xwor_tier = ET.SubElement(root, "TIER")
        xwor_tier.set("TIER_ID", f"wor@{tier_id}")
        xwor_tier.set("PARTICIPANT", tier_id)
        xwor_tier.set("LINGUISTIC_TYPE_REF", "dependency")
        xwor_tier.set("DEFAULT_LOCALE", "us")
        xwor_tier.set("PARENT_REF", tier_id)

        # we delete all previous xwor/wor tiers
        if "wor" in tier_id or "xwor" in tier_id:
            root.remove(tier)
            continue

        # we ignore anything that's a "@S*" tier
        # because those are metadata
        if "@" in tier_id:
            continue

        # For each annotation
        for annotation in tier:
            # get annotation
            annotation = annotation[0]
            # get ID
            annot_id = annotation.attrib.get("ANNOTATION_ID", "0")

            # append annotation line
            # create two element
            xwor_annot = ET.SubElement(xwor_tier, 'ANNOTATION')
            xwor_annot_cont = ET.SubElement(xwor_annot, 'REF_ANNOTATION')

            # adding annotation metadata
            xwor_annot_cont.set("ANNOTATION_ID", f"xw{id_indx}")
            xwor_annot_cont.set("ANNOTATION_REF", annot_id)

            # and add content
            xwor_word_cont = ET.SubElement(xwor_annot_cont, "ANNOTATION_VALUE")

            # with the bulleted content
            xwor_word_cont.text = terms_dict.get(annot_id)

            # update index
            id_indx += 1

    # Remove the old time slot IDs
    root[1].clear()

    # For each of the resulting annotations, dump the time values
    # Remember that time values dumped in milliseconds so we
    # multiply the result by 1000 and round to int
    for annotation, alignment in zip(annotations, alignments):
        # Create the beginning time slot
        element_start = ET.Element("TIME_SLOT")
        # Set the time slot ID to the correct beginning
        element_start.set("TIME_SLOT_ID", f"ts{annotation[0][0]}")

        # Create the beginning time slot
        element_end = ET.Element("TIME_SLOT")
        # Set the time slot ID to the correct beginning
        element_end.set("TIME_SLOT_ID", f"ts{annotation[0][1]}")

        # if alignment is not None, set time value
        if alignment:
            # Set the time slot ID to the correct end
            element_start.set("TIME_VALUE", f"{int(alignment[0]*1000)}")
            # Set the time slot ID to the correct end
            element_end.set("TIME_VALUE", f"{int(alignment[1]*1000)}")

        # Appending the element
        root[1].append(element_start)
        root[1].append(element_end)

def eafud(root, annotations, morphodata):
    """inject parsed UD results into EAF (%mor and %gra tier)

    Attributes:
        root (ET.ElementTree): element tree
        annotations (tuple(time, TIER, id)): tier information extracted from input
        morphodata (dict): raw, processed Stanza output dictionary from ud

    Returns:
        None

    Side effects:
        Modify root
    """

    # get the tiers
    tiers = root[2:]

    # breakpoint()
 

def inject_eaf(file_path, output_path, alignments=None, morphodata=None):
    """get an unaligned eaf file to be aligned

    Attributes:
        file_path (string): file path of the .eaf file
        output_path (string): output path of the aligned .eaf file
        alignments (list or dict): output of transcript word alignment
        morphodata (dict): raw, processed Stanza output dictionary from ud

    Returns:
        None
    """

    # Load the file
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file_path, parser=parser)
    root =  tree.getroot()
    tiers = root[2:]

    # create an array for annotations
    annotations = []

    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # we ignore anything that's a "@S*" tier
        # because those are metadata
        if "@" in tier_id:
            continue

        # For each annotation
        for annotation in tier:

            # Parse timeslot ID
            try: 
                timeslot_id_1 = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])
                timeslot_id_2 = int(annotation[0].attrib.get("TIME_SLOT_REF2", "0")[2:])
            except ValueError:
                print(file_path)

            # and append the metadata + transcript to the annotations
            annotations.append(((timeslot_id_1,timeslot_id_2), # (time, time)
                                tier_id, # PAR
                                annotation[0].attrib.get("ANNOTATION_ID", "0"))) # axx

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:int(x[-1][1:]))

    # if we are injecting the EAF with alignments
    if alignments:
        eafalign(root, annotations, alignments)
    # if morphodata:
    eafud(root, annotations, morphodata)

    # Indent the tree
    indent(root)
    # And write tit to file
    tree.write(output_path, encoding="unicode", xml_declaration=True)

def elan2transcript(file_path):
    """convert an eaf XML file to tiered transcripts

    Attributes:
        file_path (string): file path of the .eaf file

    Returns:
        a dictionary of shape {"transcript":transcript, "tiers":tiers},
        with two arrays with transcript information.
    """

    # Load the file
    parser = ET.XMLParser(encoding="utf-8")
    tree = ET.parse(file_path, parser=parser)
    root =  tree.getroot()
    tiers = root[2:]

    # create an array for annotations
    annotations = []

    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # we ignore anything that's a "@S*" tier
        # because those are metadata
        if "@" in tier_id:
            continue

        # For each annotation
        for annotation in tier:
            # Get the text of the transcript
            transcript = annotation[0][0].text
            # and append and sort by the time slot references
            try: 
                timeslot_id = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])
            except ValueError:
                print(file_path)

            # and append the metadata + transcript to the annotations
            annotations.append((timeslot_id, tier_id, transcript))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:x[0])

    # we will seperate the tuples after sorting
    _, tiers, transcript = zip(*annotations)

    return {"transcript":transcript, "tiers":tiers}


# chat2elan a whole path
def chat2elan(directory):
    """Convert a folder of CLAN .cha files to corresponding ELAN XMLs

    Note: this function STRIPS EXISTING TIME CODES (though,
          nondestructively)

    files:
        directory (string): the string directory in which .cha is in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.cha")
    # get the name of cleaned files
    files_cleaned = [i.replace(".cha", ".new.cha") for i in files]

    # then, clean out all bullets
    for in_file, out_file in zip(files, files_cleaned):
        # read the in file
        with open(in_file, "r") as df:
            in_file_content = df.read()

        # perform cleaning and write
        cleaned_content = re.sub("\x15.*?\x15", "", in_file_content)

        # write
        with open(out_file, "w") as df:
            df.write(cleaned_content)
            
    # chat2elan it!
    CMD = f"{os.path.join(CLAN_PATH, 'chat2elan')} +c +e.wav {' '.join(files_cleaned)} "

    # run!
    os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # delete intermediary
    for f in globase(directory, "*.new.cha"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.new.c2elan.eaf"):
        os.rename(f, f.replace(".new.c2elan.eaf", ".eaf"))


# chat2elan a whole path
def elan2chat(directory):
    """Convert a folder of CLAN .eaf files to corresponding CHATs

    files:
        directory (string): the string directory in which .elans are in

    Returns:
        None
    """
   
    # get all files in that directory
    files = globase(directory, "*.eaf")
    # process each file
    for fl in files:
        # elan2chatit!
        CMD = f"{os.path.join(CLAN_PATH, 'elan2chat +c ')} {fl} "
        # run!
        os.system(CMD)
    # delete any error logs
    for f in globase(directory, "*.err.cex"):
        os.remove(f)
    # and rename the files
    for f in globase(directory, "*.elan.cha"):
        os.rename(f, f.replace(".elan.cha", ".cha"))


