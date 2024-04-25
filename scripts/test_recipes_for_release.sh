#!/usr/bin/env bash

set -euo pipefail

# Set up variables

## Data prep
export path_to_tsv_dump_file=$1
export reverse=${reverse:-no}
export n_workers=${n_workers:-1}
export max_update_for_train=200

## Train model etc.
export seed_start=${seed_start:-1917}
export seed_end=${seed_start:-1921}

## Corpus prefix
suffix=$([ "${reverse}" == "yes" ] && echo "-rev" || echo "")
corpus_prefix="pn-tag-ablation$suffix"

## Max number of names (TEST ONLY)
export max_names_per_lang_train=1000
export max_names_per_lang_dev=100
export max_names_per_lang_test=100

# Run the scripts

## Data prep
echo "Data prep:"
echo "----------"
echo "TSV path: ${path_to_tsv_dump_file}"
echo "Reverse? ${reverse}"
echo "No. of workers: ${n_workers}"

bash recipes/tag_ablation_create_data.sh \
    "${path_to_tsv_dump_file}" \
    "${reverse}" \
    "${n_workers}" \
    "${corpus_prefix}" \
    "${max_names_per_lang_train}" \
    "${max_names_per_lang_dev}" \
    "${max_names_per_lang_test}"

## Create reverse data
echo "Reverse data prep:"
echo "------------------"
bash recipes/tag_ablation_create_reverse_data.sh \
    ${n_workers} "none"

## Train model etc.
echo "Train model etc."
echo "----------------"

bash recipes/tag_ablation_experiments.sh \
    ${seed_start} ${seed_end} ${max_update_for_train}

## Evaluation
echo "Evaluation"
echo "----------"
echo Run the below command once the training runs have finished in the background
echo 'bash recipes/tag_ablation_evaluate.sh <start seed> <end seed> <split> <num jobs per gpu>'
