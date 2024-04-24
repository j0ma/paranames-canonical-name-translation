#!/usr/bin/env bash
set -euo

SEED_START=${1:-1917}
SEED_END=${2:-$SEED_START}
MODE=${3:-dev}
JOBS_PER_GPU=${4:-3}

get_newline_separated_values () {
    local msg=$1
    echo "${msg}" | vipe | rg -v "^#"
}

if [ "${MODE}" = "dev" ]
then
    eval_name="transformer"
else
    eval_name="transformer_test"
fi

first_half=$(get_newline_separated_values "# Enter first half of experiments (remove -seed[0-9]+)")
second_half=$(get_newline_separated_values "# Enter second half to send to GPU 1 (remove -seed[0-9]+)")

# If needed, create parallel data using recipes/tag_ablation_create_data.sh

# Start 12 queues, 6 for each gpu (this assumes 2 GPUs)
for _ in $(seq 1 ${JOBS_PER_GPU})
do
    guild run queue gpus=0 --background -y
    guild run queue gpus=1 --background -y
done

for seed in $(seq $SEED_START $SEED_END)
do
    echo "Running seed: ${seed}"

    # Evaluate
    parallel echo ::: $first_half | sort |\
    while read first_corpus_name
    do
        experiment_name="${first_corpus_name}-seed${seed}"
        langs_file=$(pwd)/experiments/${experiment_name}/raw_data/${MODE}.languages
        guild run -y --stage --gpus 0 evaluate_transformer \
            experiment_name="${experiment_name}" \
            seed=$seed langs_file=$langs_file mode="${MODE}" eval_name="${eval_name}"
    done

    parallel echo ::: $second_half| sort |\
    while read second_corpus_name
    do
        experiment_name="${second_corpus_name}-seed${seed}"
        langs_file=$(pwd)/experiments/${experiment_name}/raw_data/${MODE}.languages
        guild run -y --stage --gpus 1 evaluate_transformer \
            experiment_name="${experiment_name}" \
            seed=$seed langs_file=$langs_file mode="${MODE}" eval_name="${eval_name}"
    done

done
