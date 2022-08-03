# pull conda
FROM continuumio/miniconda3

# copy all the dependency files
COPY . /root
WORKDIR /root

# install mfa
RUN conda create -n aligner -c conda-forge montreal-forced-aligner
ENV PATH /opt/conda/envs/aligner/bin:$PATH
RUN /bin/bash -c "source activate aligner"

# install torch
RUN conda install -c pytorch

# install other dependencies
RUN conda install nltk transformers tokenizers
RUN pip install rev_ai

# download models
RUN mfa model download g2p english_us_arpa
RUN mfa model download acoustic english_us_arpa

# run!
ENTRYPOINT python ./batchalign.py --retokenize /root/model -in /root/in /root/out --rev $REV_API
