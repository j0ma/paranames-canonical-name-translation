# `prep_experiment.sh`

## What it does

Creates an experiment folder with three linked folders:
- Raw data
- Binarized data
- Model checkpoints

The reason for symlinking is to make handling different filesystems easier on systems like shared HPC clusters.

## How to call

No need to call directly

## How it works

Takes the following arguments:

- Experiment name
- Optionally (see NOTE below)
	- Normalization type (defaults to `none`)
	- Corpus name (defaults to `trabina_preprocessed` <-- this is really obsolete naming)

```bash
EXPERIMENT_NAME=$1
NORMALIZATION=${2:-none}
NORMALIZATION=$(echo "$NORMALIZATION" | tr "[:upper:]" "[:lower:]")
CORPUS_NAME=${3:-trabina_preprocessed}
```

NOTE: All of these will be given when called by `recipes/tag_ablation_experiments.sh`.

Then, the script creates a dedicated folder for the experiment:

```bash
# create experiment folder
EXPERIMENT_FOLDER="${WORKING_DIR}/experiments/${EXPERIMENT_NAME}"
mkdir -p "${EXPERIMENT_FOLDER}"
```

Following that, the script symlinks the raw and binarized data folders created by [`recipes/tag_ablation_create_data.sh`](recipes_tag_ablation_create_data.md):

```bash
# infer data folders
# NOTE: change this default behavior (_noeng) if you want to include english on src side
RAW_DATA_FOLDER="${WORKING_DIR}/data/${CORPUS_NAME}/${NORMALIZATION}_normalized_noeng"
BIN_DATA_FOLDER="${WORKING_DIR}/data-bin/${CORPUS_NAME}/${NORMALIZATION}_normalized_noeng"

# symlink data folders
echo "Symlinking data folders..."
ln -vs "${RAW_DATA_FOLDER}" "${EXPERIMENT_FOLDER}/raw_data"
ln -vs "${BIN_DATA_FOLDER}" "${EXPERIMENT_FOLDER}/binarized_data"
```

Finally, create a suitable checkpoint folder and link it:

```bash
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
```