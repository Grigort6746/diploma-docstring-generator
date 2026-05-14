from __future__ import annotations

import argparse
import random
from pathlib import Path

import pandas as pd

from pipeline_common import (
    CODE_COLUMN_CANDIDATES,
    DOC_COLUMN_CANDIDATES,
    FILE_COLUMN_CANDIDATES,
    FUNCTION_COLUMN_CANDIDATES,
    REPO_COLUMN_CANDIDATES,
    canonical_code,
    find_column,
    normalize_code,
    normalize_docstring,
    quality_flags,
    read_table,
    stable_hash,
    strip_source_docstrings,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare code/docstring datasets.")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input dataset files.")
    parser.add_argument(
        "--output-dir",
        default="docstring_training_v2/data/prepared",
        help="Directory for train/validation/test parquet files.",
    )
    parser.add_argument("--code-column", default=None)
    parser.add_argument("--doc-column", default=None)
    parser.add_argument("--repo-column", default=None)
    parser.add_argument("--file-column", default=None)
    parser.add_argument("--function-column", default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-size", type=float, default=0.1)
    parser.add_argument("--test-size", type=float, default=0.1)
    parser.add_argument("--min-code-chars", type=int, default=20)
    parser.add_argument("--min-doc-chars", type=int, default=10)
    parser.add_argument("--max-code-chars", type=int, default=12000)
    parser.add_argument("--max-doc-chars", type=int, default=2000)
    parser.add_argument("--require-def", action="store_true")
    parser.add_argument("--require-google-style", action="store_true")
    parser.add_argument(
        "--keep-source-docstrings",
        action="store_true",
        help="Do not remove docstrings from the code input.",
    )
    parser.add_argument(
        "--dedupe-on",
        choices=("code", "code_doc"),
        default="code",
        help="Deduplicate by code only or by code+docstring pair.",
    )
    parser.add_argument(
        "--keep-metadata-in-splits",
        action="store_true",
        help="Keep metadata columns in train/validation/test parquet files.",
    )
    parser.add_argument(
        "--limit-per-file",
        type=int,
        default=0,
        help="Debug helper: keep only the first N rows from each input.",
    )
    return parser.parse_args()


def normalize_file(path: Path, args: argparse.Namespace) -> tuple[pd.DataFrame, list[dict]]:
    raw = read_table(path)
    if args.limit_per_file:
        raw = raw.head(args.limit_per_file)

    code_col = find_column(raw.columns, args.code_column, CODE_COLUMN_CANDIDATES)
    doc_col = find_column(raw.columns, args.doc_column, DOC_COLUMN_CANDIDATES)
    if not code_col or not doc_col:
        raise ValueError(
            f"{path}: cannot find code/docstring columns. "
            f"Found columns: {list(raw.columns)}"
        )

    repo_col = find_column(raw.columns, args.repo_column, REPO_COLUMN_CANDIDATES)
    file_col = find_column(raw.columns, args.file_column, FILE_COLUMN_CANDIDATES)
    function_col = find_column(raw.columns, args.function_column, FUNCTION_COLUMN_CANDIDATES)

    records: list[dict] = []
    rejected: list[dict] = []

    for source_row, row in raw.iterrows():
        code = normalize_code(row[code_col])
        docstring = normalize_docstring(row[doc_col])
        if not args.keep_source_docstrings:
            code = strip_source_docstrings(code)

        flags = quality_flags(
            code=code,
            docstring=docstring,
            min_code_chars=args.min_code_chars,
            min_doc_chars=args.min_doc_chars,
            max_code_chars=args.max_code_chars,
            max_doc_chars=args.max_doc_chars,
            require_def=args.require_def,
            require_google_style=args.require_google_style,
        )
        if flags:
            rejected.append(
                {
                    "source_file": str(path),
                    "source_row": int(source_row),
                    "reason": ",".join(flags),
                }
            )
            continue

        repo = normalize_docstring(row[repo_col]) if repo_col else ""
        file_path = normalize_docstring(row[file_col]) if file_col else ""
        function_name = normalize_docstring(row[function_col]) if function_col else ""
        code_hash = stable_hash(canonical_code(code))
        doc_hash = stable_hash(docstring)

        records.append(
            {
                "code": code,
                "docstring": docstring,
                "repo_url": repo,
                "file_path": file_path,
                "function_name": function_name,
                "source_file": str(path),
                "source_row": int(source_row),
                "code_hash": code_hash,
                "doc_hash": doc_hash,
                "doc_len": len(docstring),
                "code_len": len(code),
            }
        )

    return pd.DataFrame(records), rejected


def dedupe(df: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, int]:
    before = len(df)
    if df.empty:
        return df, 0

    df = df.sort_values(
        by=["doc_len", "code_len"],
        ascending=[False, True],
        kind="mergesort",
    )
    if mode == "code":
        df = df.drop_duplicates(subset=["code_hash"], keep="first")
    else:
        df = df.drop_duplicates(subset=["code_hash", "doc_hash"], keep="first")
    df = df.drop(columns=["doc_len", "code_len"])
    return df.reset_index(drop=True), before - len(df)


def split_by_repo_or_rows(
    df: pd.DataFrame,
    validation_size: float,
    test_size: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    rng = random.Random(seed)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    has_repo_groups = "repo_url" in df.columns and df["repo_url"].fillna("").str.len().gt(0).any()
    if not has_repo_groups:
        test_count = int(round(len(df) * test_size))
        val_count = int(round(len(df) * validation_size))
        test_df = df.iloc[:test_count]
        val_df = df.iloc[test_count : test_count + val_count]
        train_df = df.iloc[test_count + val_count :]
        return train_df, val_df, test_df, "row"

    group_to_indices: dict[str, list[int]] = {}
    for idx, repo in enumerate(df["repo_url"].fillna("").astype(str)):
        group = repo if repo else f"__row_{idx}"
        group_to_indices.setdefault(group, []).append(idx)

    groups = list(group_to_indices)
    rng.shuffle(groups)
    target_test = len(df) * test_size
    target_val = len(df) * validation_size
    test_indices: list[int] = []
    val_indices: list[int] = []
    train_indices: list[int] = []

    for group in groups:
        indices = group_to_indices[group]
        if len(test_indices) < target_test:
            test_indices.extend(indices)
        elif len(val_indices) < target_val:
            val_indices.extend(indices)
        else:
            train_indices.extend(indices)

    return (
        df.iloc[train_indices].reset_index(drop=True),
        df.iloc[val_indices].reset_index(drop=True),
        df.iloc[test_indices].reset_index(drop=True),
        "repo_url",
    )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    rejected_rows: list[dict] = []
    per_file: dict[str, dict] = {}

    for input_path in args.inputs:
        path = Path(input_path)
        df_part, rejected = normalize_file(path, args)
        frames.append(df_part)
        rejected_rows.extend(rejected)
        per_file[str(path)] = {
            "accepted_rows": int(len(df_part)),
            "rejected_rows": int(len(rejected)),
        }
        print(f"{path}: accepted={len(df_part)} rejected={len(rejected)}")

    if not frames:
        raise RuntimeError("No input data was loaded")

    combined = pd.concat(frames, ignore_index=True)
    before_dedupe = len(combined)
    combined, duplicate_count = dedupe(combined, args.dedupe_on)
    if combined.empty:
        raise RuntimeError("Dataset is empty after filtering and deduplication")

    train_df, val_df, test_df, split_mode = split_by_repo_or_rows(
        combined,
        validation_size=args.validation_size,
        test_size=args.test_size,
        seed=args.seed,
    )

    combined.to_parquet(output_dir / "dataset_full.parquet", index=False)

    split_columns = list(train_df.columns) if args.keep_metadata_in_splits else ["code", "docstring"]
    train_df[split_columns].to_parquet(output_dir / "train.parquet", index=False)
    val_df[split_columns].to_parquet(output_dir / "validation.parquet", index=False)
    test_df[split_columns].to_parquet(output_dir / "test.parquet", index=False)

    if rejected_rows:
        pd.DataFrame(rejected_rows).to_csv(output_dir / "rejected_rows.csv", index=False)

    report = {
        "inputs": args.inputs,
        "output_dir": str(output_dir),
        "total_before_dedupe": int(before_dedupe),
        "duplicates_removed": int(duplicate_count),
        "total_after_dedupe": int(len(combined)),
        "train_rows": int(len(train_df)),
        "validation_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "split_mode": split_mode,
        "dedupe_on": args.dedupe_on,
        "split_columns": split_columns,
        "source_docstrings_removed": not args.keep_source_docstrings,
        "per_file": per_file,
    }
    write_json(output_dir / "dataset_report.json", report)

    print("Prepared dataset")
    print(f"  full:       {len(combined)}")
    print(f"  train:      {len(train_df)}")
    print(f"  validation: {len(val_df)}")
    print(f"  test:       {len(test_df)}")
    print(f"  split:      {split_mode}")
    print(f"  output:     {output_dir}")


if __name__ == "__main__":
    main()
