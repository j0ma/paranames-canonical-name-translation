import sys
from collections import defaultdict
from typing import Dict, List, Optional, Set, TextIO, Tuple

import attr
import click
import editdistance
import jiwer
import numpy as np
import pandas as pd
import sacrebleu
from tqdm import tqdm

from util import read as read_df

"""Evaluate 2.0

Computes 5 evaluation metrics for transliterated words:
    - Character Error Rate (CER)
    - Word Accuracy
    - 1 - Word Accuracy
    - Mean F1
    - BLEU

Mean F1 is computed using longest common subsequence, which
is computed using Levenshtein distance.

All scores are normalized to lie in the range [0, 1].
"""


def read_text(path: str) -> TextIO:
    return open(path, encoding="utf-8")


@attr.s(kw_only=True)  # kw_only ensures we are explicit
class TransliterationOutput:
    """Represents a single transliteration output, consisting of a
    source language and line, reference transliteration and a model hypothesis.
    """

    language: str = attr.ib()
    reference: str = attr.ib()
    hypothesis: str = attr.ib()
    source: str = attr.ib(default="")


@attr.s(kw_only=True)
class TransliterationMetrics:
    """Score container for a collection of transliteration results.

    Contains
    - LER,
    - Word Accuracy
    - 1 - Word Accuracy
    - Mean F1
    - BLEU
    """

    character_error_rate: float = attr.ib(factory=float)
    word_acc: float = attr.ib(factory=float)
    word_err: float = attr.ib(default=1.0)
    mean_f1: float = attr.ib(factory=float)
    bleu: float = attr.ib(factory=float)
    rounding: int = attr.ib(default=5)
    language: str = attr.ib(default="")

    def __attrs_post_init__(self) -> None:
        self.character_error_rate = round(self.character_error_rate, self.rounding)
        self.word_acc = round(self.word_acc, self.rounding)
        self.word_err = round(self.word_err, self.rounding)
        self.mean_f1 = round(self.mean_f1, self.rounding)
        self.bleu = round(self.bleu, self.rounding)

    def format(self) -> str:
        """Format like in old evaluate.py"""

        out = """Word Accuracy\t{word_acc:.4f}
Mean F1\t{mean_f1:.4f}
CER\t{character_error_rate:.4f}
WER\t{word_err:.4f}
BLEU\t{bleu:.4f}\n\n""".format(
            word_acc=self.word_acc,
            mean_f1=self.mean_f1,
            character_error_rate=self.character_error_rate,
            word_err=self.word_err,
            bleu=self.bleu,
        )

        return out


@attr.s(kw_only=True)
class TransliterationResults:
    system_outputs: List[TransliterationOutput] = attr.ib(factory=list)
    metrics: TransliterationMetrics = attr.ib(factory=TransliterationMetrics)

    def __attrs_post_init__(self) -> None:
        self.metrics = self.compute_metrics()

    def compute_metrics(self) -> TransliterationMetrics:
        unique_languages = set([o.language for o in self.system_outputs])

        if len(unique_languages) > 1:
            language = "global"
        else:
            language = list(unique_languages)[0]

        character_error_rate = self.character_error_rate(self.system_outputs)
        word_acc = 100 * self.word_accuracy(self.system_outputs)
        word_err = 100 - word_acc
        bleu = 100 * self.bleu(self.system_outputs)
        mean_f1 = 100 * self.mean_f1(self.system_outputs)

        metrics = TransliterationMetrics(
            character_error_rate=character_error_rate,
            word_acc=word_acc,
            word_err=word_err,
            mean_f1=mean_f1,
            bleu=bleu,
            language=language,
        )

        return metrics

    def character_error_rate(
        self, system_outputs: List[TransliterationOutput]
    ) -> float:
        # The names are strings of space-separated characters.
        # Thus, to get CER on the original string, we compute WER
        # on the space-separated tokens.
        CER = jiwer.wer(
            [o.reference for o in system_outputs],
            [o.hypothesis for o in system_outputs],
        )

        return CER

    def word_accuracy(self, system_outputs: List[TransliterationOutput]) -> float:
        return np.mean([int(o.reference == o.hypothesis) for o in system_outputs])

    def bleu(self, system_outputs: List[TransliterationOutput]) -> float:
        hypotheses = [o.hypothesis for o in system_outputs]
        references = [[o.reference for o in system_outputs]]
        bleu = sacrebleu.corpus_bleu(hypotheses, references, force=True)

        return bleu.score / 100.0  # divide to normalize

    def mean_f1(self, system_outputs: List[TransliterationOutput]) -> float:
        return np.mean([self.f1(o.reference, o.hypothesis) for o in system_outputs])

    def f1(self, src: str, tgt: str) -> float:
        def lcs(src: str, tgt: str) -> float:
            lcs = 0.5 * ((len(src) + len(tgt)) - editdistance.eval(src, tgt))

            return lcs

        try:
            rec = lcs(src, tgt) / len(tgt)
        except ZeroDivisionError:
            rec = 0
        prec = lcs(src, tgt) / len(src)
        try:
            return 2 * ((rec * prec) / (rec + prec))
        except ZeroDivisionError:
            return 0


@attr.s(kw_only=True)
class ExperimentResults:
    system_outputs: List[TransliterationOutput] = attr.ib(factory=list)
    languages: Set[str] = attr.ib(factory=set)
    grouped: bool = attr.ib(default=True)
    metrics_dict: Dict[str, TransliterationResults] = attr.ib(factory=dict)

    def __attrs_post_init__(self) -> None:
        self.metrics_dict = self.compute_metrics_dict()

    def compute_metrics_dict(self) -> Dict[str, TransliterationResults]:
        metrics = {}

        # first compute global metrics
        metrics["global"] = TransliterationResults(system_outputs=self.system_outputs)

        # then compute one for each lang

        for lang in tqdm(self.languages, total=len(self.languages)):
            filtered_outputs = [o for o in self.system_outputs if o.language == lang]
            metrics[lang] = TransliterationResults(system_outputs=filtered_outputs)

        return metrics

    @classmethod
    def outputs_from_paths(
        cls,
        references_path: str,
        hypotheses_path: str,
        source_path: str,
        languages_path: str,
    ) -> Tuple[List[TransliterationOutput], Set[str]]:
        with read_text(hypotheses_path) as hyp, read_text(
            references_path
        ) as ref, read_text(source_path) as src, read_text(languages_path) as langs:
            languages = set()
            system_outputs = []

            for hyp_line, ref_line, src_line, langs_line in zip(hyp, ref, src, langs):
                # grab hypothesis lines
                hypothesis = hyp_line.strip()
                reference = ref_line.strip()
                source = src_line.strip()
                language = langs_line.strip()
                languages.add(language)
                system_outputs.append(
                    TransliterationOutput(
                        language=language,
                        reference=reference,
                        hypothesis=hypothesis,
                        source=source,
                    )
                )

            return system_outputs, languages

    @classmethod
    def outputs_from_combined_tsv(
        cls, combined_tsv_path: str
    ) -> Tuple[List[TransliterationOutput], Set[str]]:
        combined_tsv = read_df(
            combined_tsv_path,
            io_format="tsv",
            column_names=["ref", "hyp", "src", "language"],
            quoting=3,
        ).astype(str)

        languages = set()
        system_outputs = []

        for hypothesis, reference, source, language in tqdm(
            zip(
                combined_tsv.hyp,
                combined_tsv.ref,
                combined_tsv.src,
                combined_tsv.language,
            ),
            total=combined_tsv.shape[0],
        ):
            # grab hypothesis lines
            languages.add(language)
            system_outputs.append(
                TransliterationOutput(
                    language=language,
                    reference=reference,
                    hypothesis=hypothesis,
                    source=source,
                )
            )

        return system_outputs, languages

    @classmethod
    def from_paths(
        cls,
        references_path: str,
        hypotheses_path: str,
        source_path: str,
        languages_path: str,
        grouped: bool = True,
    ):
        system_outputs, languages = cls.outputs_from_paths(
            references_path=references_path,
            hypotheses_path=hypotheses_path,
            source_path=source_path,
            languages_path=languages_path,
        )

        return ExperimentResults(
            system_outputs=system_outputs, grouped=grouped, languages=languages
        )

    @classmethod
    def from_tsv(
        cls,
        tsv_path: str,
        grouped: bool = True,
    ):
        system_outputs, languages = cls.outputs_from_combined_tsv(tsv_path)

        return ExperimentResults(
            system_outputs=system_outputs, grouped=grouped, languages=languages
        )

    def as_data_frame(self):
        _languages = self.languages | set(["global"])

        rows = [attr.asdict(self.metrics_dict[lang].metrics) for lang in _languages]
        out = (
            pd.DataFrame(rows)
            .drop(columns=["rounding", "word_err", "bleu"])
            .rename(
                columns={
                    "character_error_rate": "CER",
                    "word_acc": "Accuracy",
                    "mean_f1": "F1",
                    "language": "Language",
                }
            )
            .round(3)
        )

        return out


@click.command()
@click.option("--references-path", "--gold-path", "--ref", "--gold", default="")
@click.option("--hypotheses-path", "--hyp", default="")
@click.option("--source-path", "--src", default="")
@click.option("--languages-path", "--langs", default="")
@click.option("--combined-tsv-path", "--tsv", default="")
@click.option("--score-output-path", "--score", default="/dev/stdout")
@click.option("--output-as-tsv", is_flag=True)
@click.option("--output-as-json", is_flag=True)
def main(
    references_path: str,
    hypotheses_path: str,
    source_path: str,
    languages_path: str,
    combined_tsv_path: str,
    score_output_path: str,
    output_as_tsv: bool,
    output_as_json: bool,
):
    if combined_tsv_path:
        results = ExperimentResults.from_tsv(tsv_path=combined_tsv_path)
    else:
        results = ExperimentResults.from_paths(
            references_path=references_path,
            hypotheses_path=hypotheses_path,
            source_path=source_path,
            languages_path=languages_path,
        )

    if output_as_tsv:
        result_df = results.as_data_frame()
        result_df.to_csv(score_output_path, index=False, sep="\t")
    else:
        with (
            open(score_output_path, "w", encoding="utf-8")

            if score_output_path
            else sys.stdout
        ) as score_out_file:
            for lang in results.languages:
                score_out_file.write(f"{lang}:\n")
                score_out_file.write(results.metrics_dict.get(lang).metrics.format())

            # finally write out global
            score_out_file.write("global:\n")
            score_out_file.write(results.metrics_dict.get("global").metrics.format())


if __name__ == "__main__":
    main()
