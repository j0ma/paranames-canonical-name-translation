#!/usr/bin/env python

from collections import defaultdict, Counter
from typing import List, Tuple, Callable, Iterable, DefaultDict, Optional, Dict, Union
from itertools import product
import math
import os

from util.script import UnicodeAnalyzer
from util import read, orjson_dump
from rich.progress import track
import pandas as pd
import numpy as np
import unicodedata
import click


def get_splits(
    num_samples: int,
    train_frac: float,
    dev_frac: float,
    test_frac: float,
    random_seed: int = 1917,
) -> Iterable[str]:

    # Set seed
    np.random.seed(random_seed)

    splits = np.array(["train", "dev", "test"])
    fractions = np.array([train_frac, dev_frac, test_frac])

    return np.random.choice(a=splits, p=fractions, size=num_samples)


def add_split_column(
    dump: pd.DataFrame,
    wikidata_id_column: str,
    split_column: str,
    train_frac: float,
    dev_frac: float,
    test_frac: float,
    random_seed: int = 1917,
) -> Tuple[pd.DataFrame, Dict[str, str]]:

    unique_wikidata_ids = Counter(
        track(
            sequence=dump[wikidata_id_column],
            description="Counting Wikidata IDs before splitting...",
            total=dump.shape[0],
        )
    )
    n_unique_ids = len(unique_wikidata_ids)

    id_to_split = {
        wid: split
        for wid, split in track(
            zip(
                unique_wikidata_ids,
                get_splits(
                    num_samples=n_unique_ids,
                    train_frac=train_frac,
                    dev_frac=dev_frac,
                    test_frac=test_frac,
                    random_seed=random_seed,
                ),
            ),
            description="Splitting unique Wikidata IDs...",
            total=n_unique_ids,
        )
    }

    dump[split_column] = pd.Categorical(
        [id_to_split[wid] for wid in dump[wikidata_id_column]],
        categories=["train", "dev", "test"],
        ordered=True,
    )

    return dump, id_to_split


def write_parallel_lines(
    lines: List[Tuple[str, str, str]], src_path: str, tgt_path: str, langs_path: str
) -> None:
    n_lines = len(lines)
    with open(langs_path, "w") as f_langs, open(
        src_path, "w", encoding="utf-8"
    ) as f_src, open(tgt_path, "w", encoding="utf-8") as f_tgt:
        for lang, src_line, tgt_line in track(
            lines, description="Writing lines to disk...", total=n_lines
        ):
            f_langs.write(f"{lang}\n")
            f_src.write(f"{src_line}\n")
            f_tgt.write(f"{tgt_line}\n")


def convert_dump_into_lines(
    dump: pd.DataFrame,
    language_column: str,
    type_column: str,
    src_column: str,
    tgt_column: str,
    wikidata_id_column: str,
    split_column: str = "split",
    filter_out_english: bool = True,
    include_language_tag: bool = True,
    include_script_tag: bool = True,
    include_type_tag: bool = True,
    reverse: bool = False,
    max_names_per_lang_train: Optional[Union[int, float]] = None,
    max_names_per_lang_dev: Optional[Union[int, float]] = None,
    max_names_per_lang_test: Optional[Union[int, float]] = None,
) -> Tuple[DefaultDict[str, List[Tuple[str, str, str]]], pd.DataFrame]:

    output_lines = defaultdict(list)
    ua = UnicodeAnalyzer(strip=True, ignore_punctuation=True, ignore_numbers=True)

    if not max_names_per_lang_train:
        max_names_per_lang_train = math.inf
    if not max_names_per_lang_dev:
        max_names_per_lang_dev = math.inf
    if not max_names_per_lang_test:
        max_names_per_lang_test = math.inf

    max_names_thresholds = {
        "train": max_names_per_lang_train,
        "dev": max_names_per_lang_dev,
        "test": max_names_per_lang_test,
    }

    print(f"Max number of names per language (train): {max_names_per_lang_train}")
    print(f"Max number of names per language (dev): {max_names_per_lang_dev}")
    print(f"Max number of names per language (test): {max_names_per_lang_test}")

    # Make sure an English side exists
    eng_column = tgt_column
    dump = dump[
        (dump[eng_column].str.len() > 0)
        & (dump[eng_column] != dump[wikidata_id_column])
    ]


    # Filter out English on the source side

    if filter_out_english:
        dump = dump[
            ~(
                (dump[language_column] == "en")
                | (dump[language_column].str.startswith("en-"))
            )
        ]

    orig_n_names_per_lang = defaultdict(Counter)
    for lang, split in zip(dump[language_column], dump[split_column]):
        orig_n_names_per_lang[lang][split] += 1

    n_names_per_lang = defaultdict(Counter)
    skipped = set()

    # Shuffle rows
    print("Shuffling rows of dump...")
    dump = dump.sample(frac=1, random_state=12345)

    for lang, conll_type, src, tgt, split in track(
        zip(
            dump[language_column],
            dump[type_column],
            dump[src_column],
            dump[tgt_column],
            dump[split_column],
        ),
        total=dump.shape[0],
        description="Converting to lines...",
    ):
        if n_names_per_lang[lang][split] >= max_names_thresholds[split]:
            if lang not in skipped:
                print(f"Max. number of names reached for {lang}. Skipping...")
            skipped.add(lang)

            continue

        try:

            src_tokens = []

            if include_language_tag:
                src_tokens.append(f"<{lang}>")

            if include_script_tag:
                script = ua.most_common_icu_script(src if not reverse else tgt)
                src_tokens.append(f"<{script}>")

            if include_type_tag:
                src_tokens.append(f"<{conll_type}>")

            src_tokens.append(" ".join(c for c in str(src)))
            src_line = " ".join(src_tokens)
            tgt_line = " ".join(c for c in str(tgt))
            output_lines[split].append((lang, src_line, tgt_line))
            n_names_per_lang[lang][split] += 1

        except:
            print(f"Error processing row: {(lang, src, tgt)}, skipping...")

    stats = pd.DataFrame(
        [
            {
                "language": lang,
                "orig_count": orig_split_count,
                "new_count": n_names_per_lang[lang][split],
                "split": split,
            }
            for lang, ctr in orig_n_names_per_lang.items()
            for split, orig_split_count in ctr.items()
        ]
    ).set_index(["split", "language"])
    total_orig = stats.orig_count.groupby(level=0).sum()
    total_new = stats.new_count.groupby(level=0).sum()
    stats["orig_frac"] = (stats.orig_count / total_orig).round(3)
    stats["new_frac"] = (stats.new_count / total_new).round(3)
    stats.sort_values("orig_count", ascending=False, inplace=True)
    stats.sort_index(axis=0, inplace=True)

    stats = stats[["orig_count", "orig_frac", "new_count", "new_frac"]]

    return output_lines, stats


@click.command()
@click.option("--dump-file")
@click.option("--wikidata-id-splits-file")
@click.option("--stats-file")
@click.option("--normalization")
@click.option(
    "--filter-out-english",
    is_flag=True,
    help="Filter out English from the non-English column",
)
@click.option("--output-folder")
@click.option("--language-column", default="language")
@click.option("--type-column", default="type")
@click.option("--src-column", default="label")
@click.option("--tgt-column", default="eng")
@click.option("--wikidata-id-column", default="wikidata_id")
@click.option("--split-column", default="split")
@click.option(
    "--include-language-tag", is_flag=True, help="Add language tag on source side"
)
@click.option(
    "--include-script-tag",
    is_flag=True,
    help="Add script tag of non-English label on source side",
)
@click.option("--include-type-tag", is_flag=True, help="Add type tag on source side")
@click.option(
    "--reverse-mode", is_flag=True, help="Reverse mode, i.e. English on source side."
)
@click.option("--train-frac", default=0.8, type=float)
@click.option("--dev-frac", default=0.1, type=float)
@click.option("--test-frac", default=0.1, type=float)
@click.option("--sampling-random-seed", type=int, default=1917)
@click.option("--max-names-per-lang-train", type=int, default=100000)
@click.option("--max-names-per-lang-dev", type=int, default=5000)
@click.option("--max-names-per-lang-test", type=int, default=5000)
def main(
    dump_file: str,
    wikidata_id_splits_file: str,
    stats_file: str,
    normalization: str,
    filter_out_english: bool,
    output_folder: str,
    language_column: str,
    type_column: str,
    src_column: str,
    tgt_column: str,
    wikidata_id_column: str,
    split_column: str,
    include_language_tag: bool = True,
    include_script_tag: bool = True,
    include_type_tag: bool = True,
    reverse_mode: bool = True,
    train_frac: float = 0.8,
    dev_frac: float = 0.1,
    test_frac: float = 0.1,
    sampling_random_seed: int = 1917,
    max_names_per_lang_train: int = 100000,
    max_names_per_lang_dev: int = 5000,
    max_names_per_lang_test: int = 5000,
) -> None:
    def unicode_normalize(word: str) -> str:
        if normalization == "none":
            return word
        else:
            return unicodedata.normalize(normalization, word)

    dump = read(dump_file, "tsv")
    dump, wikidata_id_splits = add_split_column(
        dump,
        wikidata_id_column=wikidata_id_column,
        split_column=split_column,
        train_frac=train_frac,
        dev_frac=dev_frac,
        test_frac=test_frac,
        random_seed=sampling_random_seed,
    )

    output_lines, stats_df = convert_dump_into_lines(
        dump,
        language_column,
        type_column,
        src_column,
        tgt_column,
        wikidata_id_column,
        split_column=split_column,
        include_language_tag=include_language_tag,
        include_script_tag=include_script_tag,
        include_type_tag=include_type_tag,
        filter_out_english=filter_out_english,
        reverse=reverse_mode,
        max_names_per_lang_train=max_names_per_lang_train,
        max_names_per_lang_dev=max_names_per_lang_dev,
        max_names_per_lang_test=max_names_per_lang_test,
    )

    print("Parallel data statistics:")
    print(stats_df)

    # Resolve output folder and make sure it exists

    if not output_folder:
        output_folder = "data"
        print(f'Parameter "output folder" not found. Defaulting to {output_folder}')

    output_folder = f"{output_folder}/{normalization.lower()}_normalized"

    if filter_out_english:
        output_folder = f"{output_folder}_noeng"

    if not os.path.exists(output_folder):
        print(f"Folder {output_folder} not found. Creating...")
        os.mkdir(output_folder)

    # Finally write to disk

    for split, lines in output_lines.items():
        langs_filename = f"{output_folder}/{split}.languages"
        src_filename = f"{output_folder}/{split}.src"
        tgt_filename = f"{output_folder}/{split}.tgt"
        write_parallel_lines(
            lines,
            src_path=src_filename,
            tgt_path=tgt_filename,
            langs_path=langs_filename,
        )

    if wikidata_id_splits_file:
        with open(wikidata_id_splits_file, "w") as f_splits:
            f_splits.write(orjson_dump(wikidata_id_splits))

    if stats_file:
        stats_df.to_csv(stats_file, sep="\t")


if __name__ == "__main__":
    main()
