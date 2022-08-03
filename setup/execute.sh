#!/usr/bin/env bash

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

# Prompt for mode
tput bold
echo "#### Run Configuration ####"
tput sgr0

# choose option
MODE=$(gum choose "Analyze Audio" "Align CHAT")


# # run!
# docker-compose up --build

