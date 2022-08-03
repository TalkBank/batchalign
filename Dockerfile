# pull conda
FROM continuumio/miniconda3

# copy all the dependency files
COPY . /root
WORKDIR /root

# install mfa
RUN conda config --add channels conda-forge
RUN conda install -y montreal-forced-aligner

# install torch
RUN conda install -y -c pytorch

# install other dependencies
RUN conda install -y nltk transformers tokenizers
RUN pip install rev_ai

# download models
RUN mfa model download g2p english_us_arpa
RUN mfa model download acoustic english_us_arpa

# run!
ENTRYPOINT python ./batchalign.py --retokenize /root/model -in /root/in /root/out --rev $REV_API
