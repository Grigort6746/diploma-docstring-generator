from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline_common import (
    CODE_COLUMN_CANDIDATES,
    DOC_COLUMN_CANDIDATES,
    canonical_code,
    find_column,
    normalize_code,
    normalize_docstring,
    read_table,
    stable_hash,
    strip_source_docstrings,
    write_json,
)


DEFAULT_REFERENCES = [
    "git_dataset.parquet",
    "finaly_dataset.parquet",
    "functions_with_docstrings_4.parquet",
    "functions_with_docstrings_2.parquet",
    "new_dataset.parquet",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare a candidate dataset with references.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--references", nargs="*", default=DEFAULT_REFERENCES)
    parser.add_argument("--code-column", default=None)
    parser.add_argument("--doc-column", default=None)
    parser.add_argument(
        "--keep-source-docstrings",
        action="store_true",
        help="Do not remove source docstrings before hashing code.",
    )
    parser.add_argument(
        "--report",
        default="docstring_training_v2/reports/dataset_comparison.json",
    )
    parser.add_argument(
        "--merged-output",
        default=None,
        help="Optional parquet output with candidate + references deduplicated by code.",
    )
    return parser.parse_args()


def load_normalized(
    path: str | Path,
    code_column: str | None,
    doc_column: str | None,
    keep_source_docstrings: bool,
) -> pd.DataFrame:
    path = Path(path)
    raw = read_table(path)
    code_col = find_column(raw.columns, code_column, CODE_COLUMN_CANDIDATES)
    doc_col = find_column(raw.columns, doc_column, DOC_COLUMN_CANDIDATES)
    if not code_col or not doc_col:
        raise ValueError(f"{path}: cannot find code/docstring columns")

    records: list[dict] = []
    for source_row, row in raw.iterrows():
        code = normalize_code(row[code_col])
        docstring = normalize_docstring(row[doc_col])
        if not code or not docstring:
            continue
        code_for_hash = code if keep_source_docstrings else strip_source_docstrings(code)
        records.append(
            {
                "code": code_for_hash,
                "docstring": docstring,
                "source_file": str(path),
                "source_row": int(source_row),
                "code_hash": stable_hash(canonical_code(code_for_hash)),
                "doc_hash": stable_hash(docstring),
                "code_len": len(code_for_hash),
                "doc_len": len(docstring),
            }
        )
    return pd.DataFrame(records)


def describe_frame(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "rows": 0,
            "unique_code": 0,
            "unique_pairs": 0,
            "avg_code_chars": 0,
            "avg_docstring_chars": 0,
        }
    return {
        "rows": int(len(df)),
        "unique_code": int(df["code_hash"].nunique()),
        "unique_pairs": int(df[["code_hash", "doc_hash"]].drop_duplicates().shape[0]),
        "avg_code_chars": float(round(df["code_len"].mean(), 2)),
        "avg_docstring_chars": float(round(df["doc_len"].mean(), 2)),
    }


def main() -> None:
    args = parse_args()
    candidate = load_normalized(
        args.candidate,
        args.code_column,
        args.doc_column,
        args.keep_source_docstrings,
    )
    candidate_code_hashes = set(candidate["code_hash"])
    candidate_pair_hashes = set(zip(candidate["code_hash"], candidate["doc_hash"]))

    report = {
        "candidate": {
            "path": args.candidate,
            **describe_frame(candidate),
        },
        "references": {},
    }

    all_frames = [candidate]
    print("Candidate")
    print(f"  {args.candidate}: {describe_frame(candidate)}")

    for reference in args.references:
        ref_path = Path(reference)
        if not ref_path.exists():
            report["references"][reference] = {"missing": True}
            print(f"Reference missing: {reference}")
            continue

        ref = load_normalized(
            ref_path,
            args.code_column,
            args.doc_column,
            args.keep_source_docstrings,
        )
        all_frames.append(ref)
        ref_code_hashes = set(ref["code_hash"])
        ref_pair_hashes = set(zip(ref["code_hash"], ref["doc_hash"]))
        overlap_code = candidate_code_hashes & ref_code_hashes
        overlap_pairs = candidate_pair_hashes & ref_pair_hashes
        stats = {
            **describe_frame(ref),
            "overlap_with_candidate_code": int(len(overlap_code)),
            "overlap_with_candidate_pairs": int(len(overlap_pairs)),
            "candidate_new_code_vs_reference": int(len(candidate_code_hashes - ref_code_hashes)),
        }
        report["references"][reference] = stats
        print(f"Reference: {reference}")
        print(f"  rows={stats['rows']} unique_code={stats['unique_code']}")
        print(
            "  overlap_code="
            f"{stats['overlap_with_candidate_code']} "
            "overlap_pairs="
            f"{stats['overlap_with_candidate_pairs']}"
        )

    if args.merged_output:
        merged = pd.concat(all_frames, ignore_index=True)
        before = len(merged)
        merged = merged.sort_values(
            by=["doc_len", "code_len"],
            ascending=[False, True],
            kind="mergesort",
        )
        merged = merged.drop_duplicates(subset=["code_hash"], keep="first")
        merged = merged.drop(columns=["code_len", "doc_len"])
        output_path = Path(args.merged_output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merged.to_parquet(output_path, index=False)
        report["merged_output"] = {
            "path": str(output_path),
            "rows_before_dedupe": int(before),
            "rows_after_dedupe": int(len(merged)),
        }
        print(f"Merged output: {output_path} rows={len(merged)}")

    write_json(args.report, report)
    print(f"Report written to {args.report}")


if __name__ == "__main__":
    main()
