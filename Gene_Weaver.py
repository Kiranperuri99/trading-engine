"""Gene Weaver: a small, dependency-free DNA FASTA analyzer.

Run from PowerShell or a VS Code terminal:

    py Gene_Weaver.py sample.fasta
    py Gene_Weaver.py sample.fasta --motif ATG --json

This starter analyzes sequences only. It does not make medical or diagnostic claims.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence


VALID_BASES = frozenset("ACGTN")
BASE_ORDER = "ACGTN"
COMPLEMENT_TABLE = str.maketrans("ACGTN", "TGCAN")


def normalize_sequence(raw_sequence: str) -> str:
    """Remove whitespace, use uppercase, and check for DNA/IUPAC N bases."""
    sequence = "".join(raw_sequence.split()).upper()
    if not sequence:
        raise ValueError("a sequence is empty")

    invalid_bases = sorted(set(sequence) - VALID_BASES)
    if invalid_bases:
        invalid_text = ", ".join(repr(base) for base in invalid_bases)
        raise ValueError(
            f"unsupported character(s): {invalid_text}; allowed bases are A, C, G, T, and N"
        )
    return sequence


def read_fasta(file_path: Path) -> list[tuple[str, str]]:
    """Read one or more named records from a plain-text FASTA file."""
    records: list[tuple[str, str]] = []
    header: str | None = None
    sequence_lines: list[str] = []

    def save_record() -> None:
        if header is None:
            return
        raw_sequence = "".join(sequence_lines)
        try:
            sequence = normalize_sequence(raw_sequence)
        except ValueError as error:
            raise ValueError(f"FASTA record {header!r}: {error}") from error
        records.append((header, sequence))

    for line_number, raw_line in enumerate(
        file_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith(">"):
            save_record()
            header = line[1:].strip()
            if not header:
                raise ValueError(f"FASTA header on line {line_number} is empty")
            sequence_lines = []
        else:
            if header is None:
                raise ValueError(
                    f"sequence data appears before the first FASTA header on line {line_number}"
                )
            sequence_lines.append(line)

    save_record()
    if not records:
        raise ValueError("no FASTA records were found in the input file")
    return records


def count_overlapping_motifs(sequence: str, motif: str) -> int:
    """Count motif matches, including matches that overlap one another."""
    count = 0
    start = 0
    while True:
        index = sequence.find(motif, start)
        if index == -1:
            return count
        count += 1
        start = index + 1


def analyze_sequence(
    name: str, sequence: str, motifs: Sequence[str] = ()
) -> dict[str, object]:
    """Return simple descriptive measurements for one DNA sequence."""
    base_counts = {base: sequence.count(base) for base in BASE_ORDER}
    known_base_count = sum(base_counts[base] for base in "ACGT")
    gc_count = base_counts["G"] + base_counts["C"]
    gc_percent = round(gc_count / known_base_count * 100, 2) if known_base_count else None

    return {
        "name": name,
        "length": len(sequence),
        "base_counts": base_counts,
        "gc_percent_known_bases": gc_percent,
        "reverse_complement": sequence.translate(COMPLEMENT_TABLE)[::-1],
        "motif_counts": {
            motif: count_overlapping_motifs(sequence, motif) for motif in motifs
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize DNA sequences stored in a plain-text FASTA file."
    )
    parser.add_argument("fasta", type=Path, help="path to the input FASTA file")
    parser.add_argument(
        "--motif",
        action="append",
        default=[],
        metavar="DNA",
        help="DNA motif to count; repeat this option to check several motifs",
    )
    parser.add_argument(
        "--json", action="store_true", help="print the summary as JSON"
    )
    return parser


def print_text_report(reports: Sequence[dict[str, object]]) -> None:
    for record_number, report in enumerate(reports):
        if record_number:
            print()

        print(f"Sequence: {report['name']}")
        print(f"Length: {report['length']} bases")
        counts = report["base_counts"]
        assert isinstance(counts, dict)
        print("Base counts: " + ", ".join(f"{base}={counts[base]}" for base in BASE_ORDER))

        gc_percent = report["gc_percent_known_bases"]
        if gc_percent is None:
            print("GC content: unavailable (sequence contains no A, C, G, or T bases)")
        else:
            print(f"GC content: {gc_percent}% of known bases")

        print(f"Reverse complement: {report['reverse_complement']}")
        motif_counts = report["motif_counts"]
        assert isinstance(motif_counts, dict)
        for motif, count in motif_counts.items():
            print(f"Motif {motif}: {count} overlapping occurrence(s)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        motifs = [normalize_sequence(motif) for motif in args.motif]
        records = read_fasta(args.fasta)
        reports = [analyze_sequence(name, sequence, motifs) for name, sequence in records]
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(reports, indent=2))
    else:
        print_text_report(reports)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
