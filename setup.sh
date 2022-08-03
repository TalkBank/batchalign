#!/usr/bin/env bash

# clear
clear

# Welcome the user
tput bold 
echo -e "\nWelcome to batchalign setup!"
tput sgr0 

# Print the environment
echo "We have detected your operating system as $OSTYPE." 

# detect operating system, and trigger the right command
case $OSTYPE in
    *darwin*)
        echo -n "Pulling and running the darwin setup script! " 
        /usr/bin/env bash -c "$(curl -H 'Cache-Control: no-cache' -fsSL https://raw.githubusercontent.com/TalkBank/batchalign/master/setup/darwin.sh)"
esac
