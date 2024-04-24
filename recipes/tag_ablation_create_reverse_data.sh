#!/usr/bin/env bash

n_workers=${1:-1}
unicode_normalization=${2:-none}

create_reverse_data () {

    local folder=$1
    local unicode_normalization=$2
    local n_workers=$3

    folder_path=$(dirname $folder)
    folder_name=$(basename $folder)
    reverse_folder_name=${folder_name/pn-/pn-rev-}
    reverse_folder=${folder_path}/${reverse_folder_name}
    text_input_folder=$folder/${unicode_normalization}_normalized_noeng
    text_output_folder=$reverse_folder/${unicode_normalization}_normalized_noeng

    mkdir -p $text_output_folder

    echo "Input folder: ${text_input_folder}"
    echo "Output folder: ${text_output_folder}"

    for split in "train" "dev" "test"
    do
        python scripts/swap_src_tgt.py \
            --src-input-file $text_input_folder/$split.src \
            --tgt-input-file $text_input_folder/$split.tgt \
            --src-output-file $text_output_folder/$split.src \
            --tgt-output-file $text_output_folder/$split.tgt
        cp -v \
            $text_input_folder/$split.languages \
            $text_output_folder/$split.languages
    done

    bin_folder=data-bin/$(basename $(dirname $text_output_folder))/${unicode_normalization}_normalized_noeng
    mkdir -p $bin_folder
    fairseq-preprocess \
        --source-lang src --target-lang tgt \
        --trainpref $text_output_folder/train \
        --validpref $text_output_folder/dev \
        --testpref $text_output_folder/test \
        --destdir $bin_folder \
        --workers $n_workers
}

for folder in ./data/pn-tag-ablation-{lang,script,none,lang-type,lang-script,lang-type-script}
do
    create_reverse_data $folder $unicode_normalization $n_workers &
done

wait
