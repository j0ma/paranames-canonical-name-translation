## What it is

Configuration file for `guild` experiment manager.
Responsible for running the training and evaluation workflows for the transformer models.

## Workflows

### `train_transformer`

- Runs `models/transformer/train` with appropriate training arguments

Relevant section of `guild.yml`:

```yaml
train_transformer:
  description: "Train transformer model"
  exec: "bash models/transformer/train ${seed} ${criterion} ${label_smoothing} ${optimizer} ${lr} ${lr_scheduler} ${warmup_init_lr} ${warmup_updates} ${clip_norm} ${max_update} ${save_interval} ${encoder_layers} ${encoder_attention_heads} ${decoder_layers} ${decoder_attention_heads} ${activation_fn} ${batch_size} ${p_dropout} ${decoder_embedding_dim} ${decoder_hidden_size} ${encoder_embedding_dim} ${encoder_hidden_size} ${experiment_name} ${validate_interval} ${validate_interval_updates} ${patience}"
  flags:
  - $include:
    - basic-flags
    - transformer-flags
  - requires:
    - file: data
    - file: data-bin
    - file: checkpoints
    - file: experiments
    - file: models
    - file: scripts
    - file: recipes
  - sourcecode: no
```

### `evaluate_transformer`

- Runs `models/transformer/evaluate` with appropriate arguments

Relevant section of `guild.yml`

```yaml
    evaluate_transformer:
      description: "Evaluate transformer model"
      exec: "bash models/transformer/evaluate ${experiment_name} ${mode} ${beam_size} ${seed} ${eval_name} ${langs_file} ${use_cpu}"
      flags:
        $include:
          - basic-flags
        mode:
          type: string
          default: "dev"
        beam_size:
          type: int
          default: 5
        eval_name:
          default: "transformer"
        langs_file:
          default: ""
        use_cpu:
          type: string
          default: "no"
      output-scalars:
          - word_acc: 'Word Accuracy\t(\value)'
          - mean_f1: 'Mean F1\t(\value)'
          - cer: 'CER\t(\value)'
          - wer: 'WER\t(\value)'
      requires:
        - file: data
        - file: data-bin
        - file: checkpoints
        - file: experiments
        - file: models
        - file: scripts
        - file: recipes
      sourcecode: no
      compare:
        - cer
        - wer
        - mean_f1
        - word_acc
```