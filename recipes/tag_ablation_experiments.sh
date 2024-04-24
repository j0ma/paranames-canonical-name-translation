#!/usr/bin/env bash
set -exuo pipefail

SEED_START=${1:-1917}
SEED_END=${2:-$SEED_START}
MAX_UPDATE=${3:-75000}

# If needed, create parallel data using recipes/tag_ablation_create_data.sh

# Function for grabbing values using vipe
get_newline_separated_values () {
    local msg=$1
    echo "${msg}" | vipe | rg -v "^#"
}

en2all_exps=$(get_newline_separated_values "# Enter EN - X experiments")
all2en_exps=$(get_newline_separated_values "# Enter X - EN experiments")

# Start 6 queues, 3 for each gpu (this assumes 2 GPUs)
for _ in $(seq 1 3)
do
    guild run queue gpus=0 --background -y
    guild run queue gpus=1 --background -y
done

for seed in $(seq $SEED_START $SEED_END)
do
    echo "Running seed: ${seed}"

    # Create experiment folders
    parallel echo ::: $all2en_exps | sort | \
    while read corpus_name
    do
        bash scripts/prep_experiment.sh "${corpus_name}-seed${seed}" none $corpus_name
    done

    parallel echo ::: $en2all_exps | sort | \
    while read corpus_name
    do
        bash scripts/prep_experiment.sh "${corpus_name}-seed${seed}" none $corpus_name
    done

    # Train
    parallel echo ::: $all2en_exps | sort |\
    while read corpus_name
    do
        guild run -y --stage --gpus 0 train_transformer \
            experiment_name="${corpus_name}-seed${seed}" \
            batch_size=128 patience=3 seed=$seed \
            max_update=$MAX_UPDATE
        sleep 0.5
    done

    parallel echo ::: $en2all_exps | sort |\
    while read corpus_name
    do
        guild run -y --stage --gpus 1 train_transformer \
            experiment_name="${corpus_name}-seed${seed}" \
            batch_size=128 patience=3 seed=$seed \
            max_update=$MAX_UPDATE
        sleep 0.5
    done

    # Evaluate
    # See recipes/tag_ablation_evaluate.sh for more

done
