#!/usr/bin/env bash

MODEL="https://dl.dropboxusercontent.com/s/4qhixi742955p35/model.tar.gz?dl=0"
MODELNAME="flowing-salad-6"

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

# Print the "done" as the new setup has taken over
# This file is pulled with "curl" by the welcome script; this "done"
# just tells the user that the new script has sucessfully been
# downloaded.

isdone

# Space question
echo
prompt "Please ensure 5GB of space is avaliable, press enter to continue. "

# create newline
echo

# Ok, first check if brew exists.
echo -n "Checking and installing Homebrew, if needed..." 
which -s brew
if [[ $? != 0 ]] ; then
    # Install Homebrew
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
isdone

# install gum and fzf for pretty prompts and select
echo -n "Installing prompt tools..." 
NONINTERACTIVE=1 brew install gum >/dev/null 2>&1
isdone

# create newline
echo

# install docker
if [ ! -d "/Applications/Docker.app" ]; then
    gum spin --title "Installing Docker..." -- brew install --cask docker
    printdone "Installing Docker..."
fi

# install git
if which programname >/dev/null; then
    gum spin --title "Installing Git..." -- brew install --cask docker
    printdone "Installing Git..."
fi


# open docker
gum spin --title "Opening Docker..." -- open /Applications/Docker.app
printdone "Opening Docker..."

# Wait for docker
prompt "Please press enter after Docker Desktop starts and is running. "
echo

# Ask for work location 
# Directory question
echo "We will need a empty directory to work off of."
echo -e "This is where we will put everything that we are going to use.\n"
read -e -p "Please select an empty directory (autocompletion enabled): $(tput setaf 2)" DIR
tput sgr0

# newline
echo

# get directory
pushd $DIR > /dev/null

# Removing any previous versions
rm -rf batchalign in out model

# Clone batchalign repo
gum spin --title "Cloning batchalign..." -- git clone --recursive https://github.com/TalkBank/batchalign.git
printdone "Cloning Batchalign..."

# Make in and out directories
mkdir in
mkdir out

# Get a copy of the model
# gum spin --title "Getting segmentation model..." -- wget $MODEL
# printdone "Getting segmentation model..."
# gum spin --title "Extracting segmentation model..." -- tar -xvf "model.tar.gz?dl=0"
# printdone "Extracting segmentation model..."
# mv $MODELNAME model
# rm -rf "model.tar.gz?dl=0"

echo

# Ask for Rev.AI Key
echo "In order to perform ASR, we leverage Rev.AI."
echo -e "Please provide your access key to Rev (http://rev.ai/)\n"
echo -e "This will not be shared beyond your local machine. \n"
KEY="$(gum input --placeholder "Rev.AI Key" --width 100)"

echo $KEY 
# get into batchalign
pushd batchalign > /dev/null

echo -n "Editing config..."
# create function to change paths
# creating compose file
cat docker-in.yml > docker-compose.yml 
# sed and replace key
sed -i "s/__REV_API__/$KEY/" docker-compose.yml
isdone

# updating batchalign config
gum spin --title "Updating batchalign Docker Config..." -- change

# move back
popd > /dev/null
popd > /dev/null

# final newline
echo


