#!/bin/bash
set -e

# Check prerequisites
./check-deps.sh release

export NODE_ENV=production

NAME=${PWD##*/}
BRANCH=${1:-$(git branch --show-current)}
BRANCH=${BRANCH//\//-}
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

# All platforms available in script.py
# Comment out platforms not needed for a specific study
platforms=("LinkedIn" "Instagram" "Facebook" "YouTube" "TikTok" "Netflix" "ChatGPT" "WhatsApp" "X" "Chrome")

mkdir -p releases/${TIMESTAMP}

for PLATFORM in "${platforms[@]}"; do
    echo "Building for platform: ${PLATFORM}..."
    export VITE_PLATFORM=$PLATFORM
    pnpm run build

    RELEASE_NAME="${NAME}_${PLATFORM}_${BRANCH}_${TIMESTAMP}.zip"
    cd packages/data-collector/dist
    zip -r ../../../releases/${TIMESTAMP}/${RELEASE_NAME} .
    cd ../../..
    echo "Created: releases/${TIMESTAMP}/${RELEASE_NAME}"
done

echo ""
echo "Done. ${#platforms[@]} platform releases created in releases/${TIMESTAMP}/"
