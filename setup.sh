#!/usr/bin/env bash

# detect operating system, and trigger the right command
case $OSTYPE in
    *darwin*)
        /usr/bin/env bash -c "$(curl -fsSL https://raw.githubusercontent.com/TalkBank/batchalign/master/setup/darwin.sh)"
esac
