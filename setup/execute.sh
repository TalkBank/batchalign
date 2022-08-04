#!/usr/bin/env bash

# get dir
BASEDIR=$(dirname "$0")

pushd $BASEDIR > /dev/null


# clear screen
clear

# print done
isdone () {
    tput setaf 2
    echo " Done."
    tput sgr0
}
printdone () {
    echo -n $1
    isdone
}
prompt() {
    read -rsn1 -p "$1"

    tput setaf 2
    echo "Thanks."
    tput sgr0
}

# prompt for info
tput bold
echo "Welcome to batchalign"
tput sgr0
echo "Let's configure your current run."
echo

# Prompt for mode
tput bold
echo "#### Run Configuration ####"
tput sgr0

# choose main mode option
MODE=$(gum choose --item.foreground 3 --cursor.foreground 1 "Analyze Raw Audio" "Analyze Rev.AI Output" "Realign CHAT")
echo -n "Our current run will $(tput setaf 2)$MODE"
tput sgr0
echo "."

# edit the configuration for the mode
sed -i '' "s|+.*+|+$MODE+|" docker-compose.yml

# prompt instructions
case $MODE in
    "Analyze Raw Audio")
        echo -n "Please place .wav files to analyze only"
        ;;
    "Analyze Rev.AI Output")
        echo -n "Please place .wav files and JSON from Rev.AI with paired names"
        ;;
    "Realign CHAT")
        echo -n "Please place .wav files and utterance-bulleted .CHA files"
        ;;
esac

# Prompt
open ./in
prompt " inside ./in, and tap enter. "
echo

# Run batchalign
tput bold
echo "#### Run Batchalign ####"
tput sgr0
echo "If this is your first time, the initial Docker build takes about half an hour."
echo "We are hoping to update this to be a full image and make the process quicker"
echo "in the near future."

echo

# run!
docker-compose up --build


popd > /dev/null