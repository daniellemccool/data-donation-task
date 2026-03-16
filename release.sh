#!/bin/bash
set -e

# Check prerequisites
./check-deps.sh release

export NODE_ENV=production

mkdir -p releases
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
mkdir -p releases/${TIMESTAMP}

platforms=("Facebook" "Instagram" "Twitter" "Tiktok" "Youtube")
for PLATFORM in "${platforms[@]}"; do
    export VITE_PLATFORM=$PLATFORM
    pnpm run build
    cd packages/data-collector/dist
    zip -r ../../../releases/${TIMESTAMP}/${PLATFORM}_${TIMESTAMP}.zip .
    cd ../../..
done
