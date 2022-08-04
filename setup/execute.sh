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

#Open Docker, only if is not running
if (! docker stats --no-stream ); then
    # open docker on the right version
    open /Applications/Docker.app
    # Wait until Docker daemon is running and has completed initialisation
    gum spin --title "Starting docker..." -- ; while (! docker stats --no-stream ); do sleep 1; done
    printdone "Starting docker..."
fi

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

# BUild batchalign
tput bold
echo "#### Building Batchalign ####"
tput sgr0
echo "If this is your first time, the initial Docker build takes about half an hour."
echo "We are hoping to update this to be a full image and make the process quicker"
echo "in the near future."

docker compose build

echo
# Run batchalign
tput bold
echo "#### Run Batchalign ####"
tput sgr0
echo "Welcome to batchalign!"
echo "Attaching to container, and letting the script take over."

echo

# run!
docker compose run --rm batchalign


echo
# Run batchalign
tput bold
echo "#### All Done ####"
tput sgr0
echo "Thanks for running batchalign."
open ./out

echo

popd > /dev/null
