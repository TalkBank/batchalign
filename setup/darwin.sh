#!/usr/bin/env bash

# print done
printdone () {
    echo -n $1
    tput setaf 2
    echo " Done."
    tput sgr0
}

# Print the "done" as the new setup has taken over
# This file is pulled with "curl" by the welcome script; this "done"
# just tells the user that the new script has sucessfully been
# downloaded.

tput setaf 2
echo "Done."
tput sgr0

# Space question
echo -e "\nWe are setting up batchalign for your system."
echo "This will consist the installation of a few"
echo "tools, which take about 5GB of space. Please"
echo "ensure that space is available. Please press"
read -rsn1 -p"enter to continue: "

tput setaf 2
echo "thanks."
tput sgr0

# create newline
echo

# Ok, first check if brew exists.
echo -n "Checking and installing Homebrew, if needed... " 
which -s brew
if [[ $? != 0 ]] ; then
    # Install Homebrew
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
tput setaf 2
echo "Done."
tput sgr0

# install gum and fzf for pretty prompts and select
echo -n "Installing prompt tools... " 
NONINTERACTIVE=1 brew install gum fzf >/dev/null 2>&1
tput setaf 2
echo "Done."
tput sgr0

# create newline
echo

# install docker
if [ ! -d "/Applications/Docker.app" ]; then
  gum spin --title "Installing Docker..." -- brew install --cask docker
  printdone "Installing Docker..."
fi

# open docker
gum spin --title "Opening Docker..." -- open /Applications/Docker.app
printdone "Opening Docker..."

# Wait for docker
gum input --placeholder "Please press enter after Docker Desktop starts and is running."

# Ask for work location 
# Space question
echo -e "We will need an empty directory to work"
echo "off of. This is where we will put everything that"
echo "we are going to use, like this script, models, etc."
tput setaf 3
echo -e "Please select an empty directory on the next screen.\n"
tput sgr0
read -rsn1 -p"Tap enter when you are ready: "

tput setaf 2
echo "thanks."
tput sgr0



