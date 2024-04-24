#!/usr/bin/env bash

# Creates parallel data for all 6 tag settings and stores
# the result in data/ under the appropriate corpus name.

set -euo

# Get dataset parameters
dump_tsv=$1
reverse=${2:-no}

# Allocate workers
n_workers=${3:-1}
n_workers_per_cond=$(($n_workers / 6))

# Set up corpus prefix
suffix=$([ "${reverse}" == "yes" ] && echo "-rev" || echo "")
default_corpus_prefix="pn-tag-ablation$suffix"
corpus_prefix=${4:-$default_corpus_prefix}

# Get max number of names
max_names_per_lang_train=${5:-500000}
max_names_per_lang_dev=${6:-5000}
max_names_per_lang_test=${7:-5000}

create_data () {

    local dump=$1
    local tags=$2
    local reverse=$3
    local n_workers=$4
    local corpus_prefix=$5

    local max_names_per_lang_train=$6
    local max_names_per_lang_dev=$7
    local max_names_per_lang_test=$8

    local corpus_name="${corpus_prefix}-${tags}"
    local train_frac=0.8
    local dev_frac=0.1
    local test_frac=0.1


    local include_lang=$([ -n "$(echo $tags | rg "lang")" ] && echo "yes" || echo "no")
    local include_type=$([ -n "$(echo $tags | rg "type")" ] && echo "yes" || echo "no")
    local include_script=$([ -n "$(echo $tags | rg "script")" ] && echo "yes" || echo "no")

    bash scripts/preprocess_paranames.sh \
        $corpus_name $dump \
        $train_frac $dev_frac $test_frac \
        $n_workers \
        $include_lang $include_type $include_script \
        $max_names_per_lang_train $max_names_per_lang_dev \
        $max_names_per_lang_test $reverse

}

_create_data () {
    local tags=$1
    local nworkers=$2
    create_data \
        $dump_tsv \
        $tags \
        $reverse $nworkers \
        $corpus_prefix \
        $max_names_per_lang_train \
        $max_names_per_lang_dev \
        $max_names_per_lang_test
}

# Create experiment folders
for tags_to_include in \
    "none" \
    "script" \
    "lang" \
    "lang-type" \
    "lang-script" \
    "lang-type-script"
do

    # Only parallelize if we have at least 6 workers
    if [ "${n_workers}" -lt 6 ]
    then
        echo "Processing in series using ${n_workers} workers."
        _create_data $tags_to_include $n_workers
    else
        echo "Parallelizing: ${n_workers_per_cond} out of ${n_workers} workers per child."
        _create_data $tags_to_include $n_workers_per_cond &
    fi

done

wait
