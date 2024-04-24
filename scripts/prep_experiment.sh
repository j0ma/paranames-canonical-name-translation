#!/usr/bin/env bash
set -euo pipefail

# Creates a custom folder for an experiment and 
# symlinks the relevant folders (checkpoint, data, data-bin)

EXPERIMENT_NAME=$1
NORMALIZATION=${2:-none}
NORMALIZATION=$(echo "$NORMALIZATION" | tr "[:upper:]" "[:lower:]")
CORPUS_NAME=${3:-trabina_preprocessed}
WORKING_DIR=$(pwd)

echo "Preparing folders for experiment: '${EXPERIMENT_NAME}'"

# create experiment folder
EXPERIMENT_FOLDER="${WORKING_DIR}/experiments/${EXPERIMENT_NAME}"
mkdir -p "${EXPERIMENT_FOLDER}"

# infer data folders
# NOTE: change this default behavior (_noeng) if you want to include english on src side
RAW_DATA_FOLDER="${WORKING_DIR}/data/${CORPUS_NAME}/${NORMALIZATION}_normalized_noeng"
BIN_DATA_FOLDER="${WORKING_DIR}/data-bin/${CORPUS_NAME}/${NORMALIZATION}_normalized_noeng"

# symlink data folders
echo "Symlinking data folders..."
ln -vs "${RAW_DATA_FOLDER}" "${EXPERIMENT_FOLDER}/raw_data"
ln -vs "${BIN_DATA_FOLDER}" "${EXPERIMENT_FOLDER}/binarized_data"

# create path for checkpoint folder
DATE_SLUG=$(date -u +"%Y-%m-%d-%H%M")

NORMALIZATION=$(
    echo "${BIN_DATA_FOLDER}" | 
    grep -Po "\w{3,}_normalized_noeng" | 
    tr "_" "-"
)

# no need to save these since guild will save them
CHECKPOINT_FOLDER="${WORKING_DIR}/checkpoints/${EXPERIMENT_NAME}-${DATE_SLUG}-${NORMALIZATION}"

# create checkpoint folder
echo "Creating folder for checkpoints..."
mkdir -p --verbose "${CHECKPOINT_FOLDER}"

# symlink checkpoint folder in experiment folder
echo "Symlinking checkpoint folder..."
ln -vs "${CHECKPOINT_FOLDER}" "${EXPERIMENT_FOLDER}/checkpoints"
