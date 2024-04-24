#!/usr/bin/env python

from typing import Union
from pathlib import Path

import click
from tqdm import tqdm


@click.command()
@click.option(
    "--src-input-file",
    type=click.Path(file_okay=True, dir_okay=False, readable=True, exists=True),
)
@click.option(
    "--tgt-input-file",
    type=click.Path(file_okay=True, dir_okay=False, readable=True, exists=True),
)
@click.option("--src-output-file", type=click.Path(file_okay=True))
@click.option("--tgt-output-file", type=click.Path(file_okay=True))
def main(
    src_input_file: Union[str, Path],
    tgt_input_file: Union[str, Path],
    src_output_file: Union[str, Path],
    tgt_output_file: Union[str, Path],
) -> None:

    # Convert to Path
    src_input_file = Path(src_input_file)
    tgt_input_file = Path(tgt_input_file)
    src_output_file = Path(src_output_file)
    tgt_output_file = Path(tgt_output_file)

    # Make directories if needed
    for out_file in (src_output_file, tgt_output_file):
        if not out_file.parent.exists():
            out_file.parent.mkdir(parents=True, exist_ok=True)

    with open(src_input_file, "r", encoding="utf-8") as src_in, open(
        tgt_input_file, "r", encoding="utf-8"
    ) as tgt_in, open(src_output_file, "w", encoding="utf-8") as src_out, open(
        tgt_output_file, "w", encoding="utf-8"
    ) as tgt_out:
        for src_line, tgt_line in tqdm(zip(src_in, tgt_in)):
            n_tags_appended = 0
            src_tokens = src_line.split(" ")

            # Turn source -> target, keeping tags on source side
            new_src_tokens = []
            new_tgt_tokens = []
            for src_tok in src_tokens:
                if (
                    src_tok.startswith("<")
                    and src_tok.endswith(">")
                    and len(src_tok) >= 4
                    and n_tags_appended < 3
                ):
                    new_src_tokens.append(src_tok)
                    n_tags_appended += 1
                else:
                    new_tgt_tokens.append(src_tok)

            # Turn target -> source
            tgt_tokens = tgt_line.split(" ")
            new_src_tokens.extend(tgt_tokens)

            # Write to disk
            new_src_line = " ".join(new_src_tokens)
            new_tgt_line = " ".join(new_tgt_tokens)

            # No need to add \n since they already end in one
            src_out.write(f"{new_src_line}")
            tgt_out.write(f"{new_tgt_line}")


if __name__ == "__main__":
    main()
