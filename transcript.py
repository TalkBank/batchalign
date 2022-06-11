# transcript.py
# Helper facilities to transform elan to transcripts, etc.

# XML facilities
import xml.etree.ElementTree as ET

# And glob facilities
import glob

# Also, include regex
import re

def eaf2transcript(file_path):
    """convert an eaf XML file to tiered transcripts

    Attributes:
        file_path (string): file path of the .eaf file

    Returns:
        a dictionary of shape {"transcript":transcript, "tiers":tiers},
        with two arrays with transcript information.
    """

    # Load the file
    tree = ET.parse(file_path)
    root =  tree.getroot()
    tiers = root[2:]

    # create an array for annotations
    annotations = []

    # For each tier 
    for tier in tiers:
        # get the name of the tier
        tier_id = tier.attrib.get("TIER_ID","")

        # For each annotation
        for annotation in tier:
            # Get the text of the transcript
            transcript = annotation[0][0].text
            # we will now perform some replacements
            # note that the text here is only to help
            # the aligner, because the text is not 
            # used when we are coping time back
            # Remove any disfluency marks
            transcript = re.sub(r"<(.*?)> *?\[.*?\]", r"\1", transcript)
            # Remove any interruptive marks
            transcript = transcript.replace("+/.","")
            # And timeslot ID
            timeslot_id = int(annotation[0].attrib.get("TIME_SLOT_REF1", "0")[2:])

            # and append the metadata + transcript to the annotations
            annotations.append((timeslot_id, tier_id, transcript))

    # we will sort annotations by timeslot ref
    annotations.sort(key=lambda x:x[0])

    # we will seperate the tuples after sorting
    _, tiers, transcript = zip(*annotations)

    return {"transcript":transcript, "tiers":tiers}
