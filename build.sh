#!/usr/bin/env bash

# assuming that there is already a buildx builder setup and used with capabilities of a multiplatform build
# between linux/arm64 and linux/amd64. Perhaps this means including a remote builder.

# build base (shouldn't be needed, takes about 5 hours!)
# sudo docker buildx build . --platform=linux/arm64,linux/amd64 --cache-to=type=registry,ref=jemokajack/batchalign:cache__base,mode=max --tag=jemokajack/batchalign:latest --target=base --push --memory-swap -1 --cache-from=type=registry,ref=jemokajack/batchalign:cache__base

# build program
sudo docker buildx build . --platform=linux/arm64,linux/amd64 --cache-to=type=registry,ref=jemokajack/batchalign:cache__program,mode=max --tag=jemokajack/batchalign:latest --target=program --push --memory-swap -1 --cache-from=type=registry,ref=jemokajack/batchalign:cache__program
