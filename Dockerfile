# Base builder stage, with packages, etc.
# pull conda
FROM continuumio/miniconda3 AS base

# install zip and build utility
RUN apt-get update
RUN apt-get install -y zip unzip
RUN apt-get install -y build-essential git aptitude

# install cmake and other build tools 
RUN apt-get install -y libopenblas-dev automake autoconf sox gfortran libtool python zlib1g-dev

# install kaldi
RUN git clone --recursive https://github.com/kaldi-asr/kaldi.git
# KEEP THE FOLLWING LINE to keep cache
RUN mkdir -p ./kaldi/tools/python/

# make tools
WORKDIR ./kaldi/tools
RUN ./extras/check_dependencies.sh
RUN make -j 2

# make source
WORKDIR ../src
RUN  cd ../tools; extras/install_openblas.sh
RUN ./configure --shared --mathlib=OPENBLAS
RUN make depend -j 2
RUN make -j 2

# copy tools
RUN cp bin/* /usr/bin
RUN cp lib/* /usr/lib
RUN cp lib/* /usr/lib

# Python time
WORKDIR /root
RUN conda install python=3.8

# install openFST
RUN apt-get install -y curl
RUN curl https://www.openfst.org/twiki/pub/FST/FstDownload/openfst-1.8.2.tar.gz -o openfst
RUN tar -xzf openfst
WORKDIR ./openfst-1.8.2
RUN ./configure --enable-far=true  --enable-bin=false --enable-mpdt=true  --enable-pdt=true
RUN make -j4
RUN make install

# install pynini
RUN pip install Cython
RUN dpkg --print-architecture
RUN pip install pynini

# install MFA
RUN pip3 install git+https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner.git

# install torch
RUN conda install -y pytorch -c pytorch

# install other dependencies
RUN conda install -y nltk transformers tokenizers
RUN pip install rev_ai

# copy more kaldi dependencies
# remove extra makefiles
RUN rm /kaldi/src/*bin/Makefile
RUN cp -r /kaldi/src/*bin/* /usr/bin
RUN cp -r /kaldi/tools/openfst*/lib/* /usr/lib

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

# remove all build cache
RUN rm -r /root/*

# install ffmpeg
RUN apt-get install -y ffmpeg

# export wheels for packages
RUN mkdir /wheelhouse
RUN pip wheel --wheel-dir=/wheelhouse Montreal-Forced-Aligner
RUN pip wheel --wheel-dir=/wheelhouse pynini

# main stage
# pull conda again
FROM continuumio/miniconda3 as program

# install python for paths
RUN conda install -y python=3.8

# copy all files
COPY --from=base /opt /opt
COPY --from=base /usr /usr
COPY --from=base /etc /etc
COPY --from=base /lib /lib
COPY --from=base /wheelhouse /wheelhouse

# install dependencies
RUN pip install --no-index --find-links=/wheelhouse Montreal-Forced-Aligner pynini

# download models
RUN mfa model download g2p english_us_arpa
RUN mfa model download acoustic english_us_arpa

# copy all the dependency files
COPY . /root
WORKDIR /root

# make runner executable
RUN chmod +x ./run.sh

# run!
ENTRYPOINT ./run.sh
