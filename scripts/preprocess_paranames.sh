#!/usr/bin/env bash

set -euo pipefail

# Preprocesses the ParaNames data

[ $# -lt 2 ] \
    && echo "Usage: preprocess_paranames.sh corpus_name dump_tsv [train_frac=0.8] [dev_frac=0.1] [test_frac=0.1] [n_workers=1] [include_lang_tag=yes] [include_type_tag=no] [include_script_tag=no] [max_names_per_lang_train=100000] [max_names_per_lang_dev=5000] [max_names_per_lang_test=5000] [reverse=no]" \
    && exit 1

CORPUS_NAME=$1
DUMP_TSV=$2
TRAIN_FRAC=${3:-0.8}
DEV_FRAC=${4:-0.1}
TEST_FRAC=${5:-0.1}
N_WORKERS=${6:-1}
INCLUDE_LANG_TAG=${7:-yes}
INCLUDE_TYPE_TAG=${8:-no}
INCLUDE_SCRIPT_TAG=${9:-no}

# Cap the number of names per language at 1m
MAX_NAMES_PER_LANG_TRAIN=${10:-1000000}
MAX_NAMES_PER_LANG_DEV=${11:-5000}
MAX_NAMES_PER_LANG_TEST=${12:-5000}

# Should src and tgt be reversed
REVERSE=${13:-no}

# Constants (change if needed)
ID_COLUMN="wikidata_id"
UNICODE_NORMALIZATION="none"

OUTPUT=data/${CORPUS_NAME}
BIN_OUTPUT=data-bin/${CORPUS_NAME}

# File in which parallel data statistics will be stored
DATA_STATS_FILE="${OUTPUT}/${UNICODE_NORMALIZATION}_normalized_noeng/parallel_data_stats.tsv"

# File in which Wikidata ID splits will be stored
ID_SPLITS_OUTPUT_FILE="${OUTPUT}/${UNICODE_NORMALIZATION}_normalized_noeng/wikidata_id_splits.json"
ID_SPLITS_RANDOM_SEED=1917

mkdir -p "$OUTPUT"
mkdir -p "$BIN_OUTPUT"

# Step 1: Prepare parallel data from dump
python scripts/prep_parallel_data.py \
    --dump-file $DUMP_TSV \
    --train-frac $TRAIN_FRAC \
    --dev-frac $DEV_FRAC \
    --test-frac $TEST_FRAC \
    --normalization "$UNICODE_NORMALIZATION" \
    --output-folder $OUTPUT \
    --filter-out-english \
    $([ "$INCLUDE_TYPE_TAG" = "yes" ] && echo "--include-type-tag")\
    $([ "$INCLUDE_LANG_TAG" = "yes" ] && echo "--include-language-tag")\
    $([ "$INCLUDE_SCRIPT_TAG" = "yes" ] && echo "--include-script-tag")\
    --src-column $([ "$REVERSE" = "no" ] && echo "label" || echo "eng")\
    --tgt-column $([ "$REVERSE" = "no" ] && echo "eng" || echo "label")\
    $([ "$REVERSE" = "yes" ] && echo "--reverse-mode")\
    --wikidata-id-column "wikidata_id" \
    --wikidata-id-splits-file $ID_SPLITS_OUTPUT_FILE \
    --sampling-random-seed $ID_SPLITS_RANDOM_SEED \
    --max-names-per-lang-train $MAX_NAMES_PER_LANG_TRAIN \
    --max-names-per-lang-dev $MAX_NAMES_PER_LANG_DEV \
    --max-names-per-lang-test $MAX_NAMES_PER_LANG_TEST \
    --stats-file $DATA_STATS_FILE
 
# Step 2: Binarize data
FOLDER=$OUTPUT/${UNICODE_NORMALIZATION}_normalized_noeng
BIN_FOLDER=$BIN_OUTPUT/$(basename $FOLDER)
mkdir -p $BIN_FOLDER
fairseq-preprocess \
    --source-lang src --target-lang tgt \
    --trainpref $FOLDER/train \
    --validpref $FOLDER/dev \
    --testpref $FOLDER/test \
    --destdir $BIN_FOLDER \
    --workers $N_WORKERS
