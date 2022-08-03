#!/usr/bin/env bash

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
MODE=$(gum choose "Analyze Raw Audio" "Analyze Rev.AI Output" "Realign CHAT")
echo -n "Our current run will $(tput setaf 2)$MODE"
tput sgr0
echo "."

case $MODE in
    "Analyze Raw Audio")
        echo "test"
        ;;
esac

# run!
docker-compose up --build

