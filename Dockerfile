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

# install zip and build utility
RUN apt-get update
RUN apt-get install -y zip unzip
RUN apt-get install -y build-essential

# install UnixClan
RUN wget https://dali.talkbank.org/clan/unix-clan.zip
# unzip unix clan
RUN unzip unix-clan.zip
WORKDIR ./unix-clan/src
# create new makefile
RUN printf "CC = g++\nCFLAGS = -O -DUNX -Wall" >> makefile
# build
RUN make -j4
WORKDIR ../unix/
# install
RUN cp bin/* /usr/bin
RUN cp obj/* /usr/lib

# copy all the dependency files
COPY . /root
WORKDIR /root

# make runner executable
RUN chmod +x ./run.sh

# run!
ENTRYPOINT ./run.sh
