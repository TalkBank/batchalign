# system utilities
import re
import string
import random

# tokenization utilitise
from nltk import word_tokenize, sent_tokenize

# torch
import torch
from torch.utils.data import dataset 
from torch.utils.data.dataloader import DataLoader
from torch.optim import AdamW

# import huggingface utils
from transformers import AutoTokenizer, BertForTokenClassification
from transformers import DataCollatorForTokenClassification

# tqdm
from tqdm import tqdm

# wandb
import wandb

# seed model
class TokenizeEngine(object):

    # seed device and tokens
    DEVICE = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

    def __init__(self, model):
        # seed tokenizers and model
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.model = BertForTokenClassification.from_pretrained(model).to(DEVICE)

        # eval mode
        self.model.eval()

    def __call__(self, passage):
        # pass it through the tokenizer and model
        tokd = tokenizer([passage], return_tensors='pt').to(DEVICE)

        # pass it through the model
        res = self.model(**tokd).logits

        # argmax
        classified_targets = torch.argmax(res, dim=2).cpu()

        # 0, normal word
        # 1, first capital
        # 2, period
        # 3, question mark
        # 4, exclaimation mark
        # 5, comma

        # get the words from the sentence
        tokenized_result = self.tokenizer.tokenize(passage)
        labeled_result = list(zip(tokenized_result, classified_targets[0].tolist()[1:-1]))

        # and finally append the result
        res_toks = []

        # for each word, perform the action
        for word, action in labeled_result:
            # set the working variable
            w = word

            # perform the edit actions
            if action == 1:
                w[0] = w[0].upper()
            elif action == 2:
                w = w+'.'
            elif action == 3:
                w = w+'?'
            elif action == 4:
                w = w+'!'
            elif action == 5:
                w = w+','

            # append
            res_toks.append(w)

        # compose final passage
        final_passage = self.tokenizer.convert_tokens_to_string(res_toks)
        split_passage = sent_tokenize(final_passage)

        return split_passage

