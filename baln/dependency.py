import stanza
from stanza.pipeline.core import CONSTITUENCY

nlp = stanza.Pipeline('en', processors='tokenize,pos,lemma,depparse')

test = nlp("If you use the biomedical and clinical model packages in Stanza, please also cite our JAMIA biomedical models paper. I am a large chicken.")

sentences = test.sentences

def parse_sentence(sentence):
    """Parses Stanza sentence into %mor and %gra strings

    Arguments:
        sentence: the stanza sentence object

    Returns:
        (str, str): (mor_string, gra_string)---strings matching
                    the output to be returned to %mor and %gra
    """

    # parse analysis results
    mor = []
    gra = []

    for indx, word in enumerate(sentence.words):
        # parse the UNIVERSAL parts of speech
        mor.append(f"{word.upos.lower()}|{word.lemma}")
        # +1 because we are 1-indexed
        # and .head is also 1-indexed already
        gra.append(f"{indx+1}|{word.head}|{word.deprel.upper()}")

    mor_str = (" ".join(mor)).strip()
    gra_str = (" ".join(gra)).strip()

    return (mor_str, gra_str)

parse_sentence(sentences[0])

words = sentences[0].words
words[4].upos
words[4].lemma
for indx, word in enumerate(words):
    # +1 because we are 1-indexed
    # and .head is also 1-indexed already
    print(f"{indx+1}|{word.head}|{word.deprel.upper()}")


from stanza.utils.conll import CoNLL
CoNLL.write_doc2conll(test, "output.conllu")
