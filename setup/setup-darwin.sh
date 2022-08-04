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

#### SETUP ####

# heading
tput bold
echo "#### Initial Setup ####"
tput sgr0

# Ok, first check if brew exists.
echo -n "Checking and installing Homebrew, if needed..." 
which -s brew
if [[ $? != 0 ]] ; then
    # Install Homebrew
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
isdone

# install gum for pretty prompts and select
if ! command -v gum &> /dev/null; then
    echo -n "Installing prompt tools..." 
    NONINTERACTIVE=1 brew install gum >/dev/null 2>&1
    isdone
    # create newline
    echo
fi

# install docker
if [ ! -d "/Applications/Docker.app" ]; then
    gum spin --title "Installing Docker..." -- brew install --cask docker
    printdone "Installing Docker..."
fi

# install git
if ! command -v git &> /dev/null; then
    gum spin --title "Installing Git..." -- brew install git
    printdone "Installing Git..."
fi

# install wget
if ! command -v wget &> /dev/null; then
    gum spin --title "Installing wget..." -- brew install wget
    printdone "Installing wget..."
fi

# install coreutils
if ! command -v wget &> /dev/null; then
    gum spin --title "Installing coreutils..." -- brew install coreutils
    printdone "Installing coreutils..."
fi

echo

#### SETUP ####

# create newline
tput bold
echo "#### Install Location ####"
tput sgr0

# Ask for work location 
# Directory question
echo "We will need a empty directory to work off of."
echo "This is where we will put everything that we are going to use."
read -e -p "Please select an empty directory (tab-completion and creation enabled): $(tput setaf 2)" DIR
DIR="${DIR/#\~/$HOME}"
tput sgr0
mkdir -p "$DIR"

# newline
echo

tput bold
echo "#### Configuration ####"
tput sgr0

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
gum spin --title "Getting segmentation model..." -- wget $MODEL
printdone "Getting segmentation model..."
gum spin --title "Extracting segmentation model..." -- tar -xvf "model.tar.gz?dl=0"
printdone "Extracting segmentation model..."
mv $MODELNAME model
rm -rf "model.tar.gz?dl=0"

echo

# Ask for Rev.AI Key
echo "In order to perform ASR, we leverage Rev.AI."
echo -e "Please provide your access key to Rev (http://rev.ai/)\n"
echo -e "This will not be shared beyond your local machine. \n"
KEY="$(gum input --placeholder "Rev.AI Key" --width 100)"

# get into batchalign
pushd batchalign > /dev/null

# remove git
rm -rf .git

echo -n "Editing config..."
# create function to change paths
# creating compose file
cat docker-in.yml > docker-compose.yml 
# sed and replace key
sed -i '' "s|__REV_API__|$KEY|" docker-compose.yml
sed -i '' "s|__IN_PATH__|$(realpath ../in)|" docker-compose.yml
sed -i '' "s|__OUT_PATH__|$(realpath ../out)|" docker-compose.yml
sed -i '' "s|__MODEL_PATH__|$(realpath ../model)|" docker-compose.yml
isdone

# Moving user files out
echo -n "Copying files..."
mv ./docker-compose.yml ../
mv ./setup/execute.sh ../execute
chmod +x ../execute
isdone

# move back
popd > /dev/null
popd > /dev/null

# Run instructions
# newline
echo

tput bold
echo "#### Configuration ####"
tput sgr0

echo "To run batchalign:"
tput setaf 2
echo -n "Please double click on the $(realpath ../execute) executable "
tput sgr0
echo "and follow its instructions."

# final newline
echo


