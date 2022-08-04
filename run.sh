#!/usr/bin/env bash

# copy contents
cd /root
mkdir work

# go to workdir
pushd work > /dev/null

# make real in and out
mkdir in
mkdir out

# cd in and copy files
cp -r /root/in/* ./in

# run!
REV_API=$REV_API BA_MODE=$BA_MODE python ../batchalign.py --retokenize /root/model /root/work/in /root/work/out

# copy output
cp -r /root/work/out/*.cha /root/out
popd > /dev/null
