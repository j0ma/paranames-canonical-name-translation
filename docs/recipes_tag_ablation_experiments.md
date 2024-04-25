# `tag_ablation_experiments.sh`

## What it does

- Requires user to run [recipes/tag_ablation_create_data.sh](recipes_tag_ablation_create_data.md) to create parallel data first
- Creates experiment folders using [`scripts/prep_experiment.sh`](scripts_prep_experiment.md)
- Trains transformer model using `guild`

Related scripts:
- [`scripts/prep_experiment.sh`](scripts_prep_experiment.md)
- [`guildfile`](guildfile.md)

## How to run

```
bash recipes/tag_ablation_experiments.sh \
    ${seed_start} ${seed_end} \
    [optional arguments]
```

The `[optional arguments]` are explained below.

## How it works

### Before running
Use [recipes/tag_ablation_create_data.sh](recipes_tag_ablation_create_data.md) to create parallel data.

### Inputs 

Four arguments (all optional): 
- Optionally
	- Start seed (default: 1917)
	- End seed (default: 1917)
	- Max number of updates: (default: 75000)

```bash
SEED_START=${1:-1917}
SEED_END=${2:-$SEED_START}
MAX_UPDATE=${3:-75000}
```


Uses `vipe` to get the list of experiments to run from the user:

```bash
# Function for grabbing values using vipe
get_newline_separated_values () {
    local msg=$1
    echo "${msg}" | vipe | rg -v "^#"
}

en2all_exps=$(get_newline_separated_values "# Enter EN - X experiments")
all2en_exps=$(get_newline_separated_values "# Enter X - EN experiments")
```

When `get_newline_separated_values` runs, a `vim` buffer will open into which you should paste the dataset names that you wish to run.
A handy way to do this is to run a bash command in the vim buffer as a filter, e.g.

```
# type this in the vim/vipe buffer
## this grabs everything in the EN-X direction
ls ./data/ | rg rev 

## alternatively use this to grab everything in the X-EN direction
ls ./data/ | rg -v rev 

# then navigate the cursor on top of the line, press !! and type "bash" followed by Enter.
# this should replace the above command with a list of files from ./data/ matching what you want to run. :)
```

Assuming there are 2 GPUs and we wish to run 3 jobs per GPU, start 6 queues using `guild`:

```bash
# Start 6 queues, 3 for each gpu (this assumes 2 GPUs)
for _ in $(seq 1 3)
do
    guild run queue gpus=0 --background -y
    guild run queue gpus=1 --background -y
done
```

(note: these can be altered as needed)

Then, the script loops over `${seed}` values. In the inner loop, the script calls `scripts/prep_experiment.sh` to prepare an experiment folder for each corpus:

```bash
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
```

Given the experiment folders, the script runs the experiments using `guild` and the workflow `train_transformer`:

```bash
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
```

The `train_transformer` workflow is described in the [guildfile](guildfile.md)

After training is done, the user can call [recipes/tag_ablation_evaluate.sh](recipes_tag_ablation_evaluate.md)