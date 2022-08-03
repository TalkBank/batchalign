#!/usr/bin/env bash

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





