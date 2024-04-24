# `tag_ablation_create_reverse_data.sh`

## What it does

Creates a reversed dataset from an already existing parallel dataset. 

The "raison d'être" for this script are the various tags that can complicate things as they must only be present on the source side, not on the target side.

Simply reversing source and target languages would not take care of this.


## How to run

This script should only be run after creating the regular data. The following must exist:
- `./data/pn-tag-ablation-lang`
- `./data/pn-tag-ablation-script`
- `./data/pn-tag-ablation-none`
- `./data/pn-tag-ablation-lang-type`
- `./data/pn-tag-ablation-lang-script`
- `./data/pn-tag-ablation-lang-type-script`

Once those exist, it is possible to simply run

```bash
bash recipes/tag_ablation_create_reverse_data.sh \
	[optional number of workers] \
	[optional normalization type]
```

## How it works

First the script takes in arguments:
- Number of workers (default: 1)
- Unicode normalization (default: `none`)

```bash
n_workers=${1:-1}
unicode_normalization=${2:-none}
```

Then, the script calls `create_reverse_data` in parallel for each of:
- `./data/pn-tag-ablation-lang`
- `./data/pn-tag-ablation-script`
- `./data/pn-tag-ablation-none`
- `./data/pn-tag-ablation-lang-type`
- `./data/pn-tag-ablation-lang-script`
- `./data/pn-tag-ablation-lang-type-script`


```bash
for folder in ./data/pn-tag-ablation-{lang,script,none,lang-type,lang-script,lang-type-script}
do
    create_reverse_data $folder $unicode_normalization $n_workers &
done

wait
```

The function `create_reverse_data` consists of three parts. First, there is some argument handling and input/output folder creation:

```bash
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

	# [...]
```

Then,  there is a call `scripts/swap_src_tgt.py` for each split (`train`, `dev`, `test`):

```bash
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
	
	# [...]
```

After swapping source and target, we call `fairseq-preprocess` to binarize the data:

```bash
	# [...]
	
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

```