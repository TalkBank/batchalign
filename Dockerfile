# pull conda
FROM continuumio/miniconda3

# install mfa
RUN conda config --add channels conda-forge
RUN conda install -y montreal-forced-aligner

# install torch
RUN conda install -y pytorch -c pytorch

# install other dependencies
RUN conda install -y nltk transformers tokenizers
RUN pip install rev_ai

# download models
RUN mfa model download g2p english_us_arpa
RUN mfa model download acoustic english_us_arpa

# install UnixClan
RUN wget https://dali.talkbank.org/clan/unix-clan.zip
RUN unzip unix-clan.zip
WORKDIR ./unix-clan/src
RUN (echo "CC = g++"; cat makefile) > makefile
RUN make -j12
WORKDIR ../unix/
RUN cp bin/* /usr/bin
RUN cp obj/* /usr/lib

# copy all the dependency files
COPY . /root
WORKDIR /root

# run!
ENTRYPOINT REV_API=$REV_API BA_MODE=$BA_MODE python ./batchalign.py --retokenize /root/model /root/in /root/out
