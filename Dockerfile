# pull conda
FROM continuumio/miniconda3

# copy all the dependency files
COPY . /root
WORKDIR /root

# install dependencies
RUN ./setup.sh

# configure entrypoint
ENTRYPOINT python ./batchalign.py --retokenize /root/model -in /root/in /root/out --rev $REV_API

