"""
featurize.py
Takes audio samples and featurize them into standard features
"""

# h5py data
import h5py

# pathing tools
import os
from pathlib import Path

# data types
from abc import ABC, abstractstaticmethod
from enum import Enum
from collections import defaultdict

import numpy as np

# import utilities
from .utils import *

class FProcessorAction(Enum):
    EXPERIMENT = 0
    TIER = 1
    UTTERANCE = 2

class FProcessor(ABC):
    produces_scalar = False

    @abstractstaticmethod
    def process(payload, active_region=None):
        pass

class FAudioProcessor(FProcessor):
    @abstractstaticmethod
    def process(audio_file:str, timestamps:list):
        pass

class FBulletProcessor(FProcessor):
    @abstractstaticmethod
    def process(bullet_array:list):
        pass

class Featurizer(object):

    def __init__(self):

        self.__experiment_processors = []
        self.__tier_processors = []
        self.__utterance_processors = []

    def register_processor(self, name, processor:FProcessor, 
                           processor_action:FProcessorAction):

        if processor_action == FProcessorAction.EXPERIMENT:
            self.__experiment_processors.append((name, processor))
        elif processor_action == FProcessorAction.TIER:
            self.__tier_processors.append((name, processor))
        elif processor_action == FProcessorAction.UTTERANCE:
            self.__utterance_processors.append((name, processor))
        else:
            raise ValueError(f"Batchalign: processor action {processor_action} unknown!")

    @staticmethod
    def __process_with(processors, bullets, alignments, audio):
        """Process a set of data with a set of processors

        Attributes:
            processors ([FProcessor]): list of processors to use
            bullets ([[("word", (beg, end)) ...] ...]): list of utterances contining list of words
            audio (str): audio file path
        """

        processed = {"scalars": {},
                     "vectors": {}}
        
        for name, i in processors:
            scalarp = "scalars" if i.produces_scalar else "vectors"
            if issubclass(i, FAudioProcessor):
                processed[scalarp][name] = i.process(audio, alignments)
            elif issubclass(i, FBulletProcessor):
                processed[scalarp][name] = i.process(bullets)
            else:
                raise ValueError(f"Batchalign: processor type {type(i)} unknown!")

        return processed

    def process(self, data, audio):
        """Process a bullet dataset

        Attributes:
            data ({"alignments": ..., "raw": ..., "tiers": ...}): the raw alignment data
            audio (str): audio file path

        Returns:
            {"experiment": {"scalars":, ...}, "tier": {...}, "utterance": {..}}
        """

        # process experiment level
        experiment_processed = self.__process_with(self.__experiment_processors,
                                                data["raw"], data["alignments"],
                                                audio)

        # process tier level (sorry for the code quality)
        # get tier ids
        id_list = defaultdict(lambda : len(id_list))
        id_indx = defaultdict(list)
        for i, tier in enumerate(data["tiers"]):
            id_indx[id_list[tier]].append(i)
        id_list = {v:k for k,v in id_list.items()} # list of {id: tier} (i.e. {0: PAR, 1: INV})
        id_indx = dict(id_indx) # get the indicies for the tier {id: [ids ...]} (i.e. {0: [0,1,2,3, ...]})
        # slice out tiers and process
        tier_processed = {}
        for key, value in id_indx.items():
            tier = id_list[key]

            alignments = [data["alignments"][i] for i in value]
            raw = [data["raw"][i] for i in value]

            tier_processed[tier] = self.__process_with(self.__tier_processors,
                                                    raw, alignments,
                                                    audio)
        # process utterance level
        utterance_processed = []

        for raw, alignments in zip(data["raw"], data["alignments"]):
            result = self.__process_with(self.__utterance_processors,
                                        [raw], [alignments],
                                        audio)

            utterance_processed.append(result)

        return { "experiment": experiment_processed,
                 "tier": tier_processed,
                 "utterance": utterance_processed }

###### Actual Processors ######

class MLU(FBulletProcessor):

    produces_scalar = True

    @staticmethod
    def process(bullet_array:list):
        # get number of utterances
        num_utterances = len(bullet_array)
        # TODO TODO BAD get the numer of morphemes 
        num_morphemes = [len(i) for i in bullet_array]

        return sum(num_morphemes)/num_utterances

###### Create Default Featurizer ######
featurizer = Featurizer()
featurizer.register_processor("mlu", MLU, FProcessorAction.TIER)

###### Normal Commands ######
def store_to_group(group, feature_dict):
    """Store a part of a feature dictioray to HDF5 group

    Attributes:
        group (hdf5.Group): the hdf5 group to store data
        feature_dict ({"vectors": ..., "scalars": ...}): the data to encode

    Used for side effects.
    """
    # store experiment scalars
    for k,v in feature_dict["scalars"].items():
        group.attrs[k] = v

    # and the datasets, which should be numpy arrays
    for k,v in feature_dict["vectors"].items():
        group.create_dataset(k, data=v)

def featurize(alignment, in_dir, out_dir, data_dir="data", lang="en", clean=True):

    for filename, data in alignment:
        # experiment name
        name = Path(filename).stem
        # generate the paths to things
        audio = os.path.join(in_dir, f"{name}.wav")
        hdf5 = os.path.join(out_dir, f"{name}.hdf5")
        chat = os.path.join(out_dir, f"{name}.cha")
        
        # featurize!
        features = featurizer.process(data, audio)

        # store the features
        f = h5py.File(hdf5, "w")
        f.attrs["num_utterances"] = len(data["raw"])

        # create the initial groups
        exp = f.create_group("experiment")
        tier = f.create_group("tier")
        utterance = f.create_group("utterance")

        # store experiment-wide results
        store_to_group(f, features["experiment"])

        # store per-tier results
        for tier_name, value in features["tier"].items():
            tier_grp = tier.create_group(tier_name)
            store_to_group(tier_grp, value)

        # store per-utterance results
        for i, value in enumerate(features["utterance"]):
            utt_grp = utterance.create_group(str(i))
            store_to_group(utt_grp, value)

        f.close()



# f = h5py.File("../../talkbank-alignment/tmp.hdf5", "w")
# f.attrs["temp"] = 1
# f.attrs.keys()
# f.close()




