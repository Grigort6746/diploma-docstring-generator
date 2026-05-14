from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_INPUTS = [
    "docstring_training_v2/functions_with_docstrings_5.parquet",
    "docstring_training_v2/git_big_dataset.parquet",
    "functions_with_docstrings_4.parquet",
    "functions_with_docstrings_2.parquet",
    "functions_with_docstrings.parquet",
    "git_dataset.parquet",
    "finaly_dataset.parquet",
    "data.parquet",
    "csn_python_filtered",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the largest deduplicated docstring dataset from known sources."
    )
    parser.add_argument(
        "--extra-inputs",
        nargs="*",
        default=[],
        help="Additional dataset files or Hugging Face dataset directories.",
    )
    parser.add_argument(
        "--output-dir",
        default="docstring_training_v2/data/max_merged",
    )
    parser.add_argument("--validation-size", type=float, default=0.08)
    parser.add_argument("--test-size", type=float, default=0.08)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Skip missing default inputs instead of failing.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inputs = DEFAULT_INPUTS + args.extra_inputs
    if args.allow_missing:
        inputs = [path for path in inputs if Path(path).exists()]

    missing = [path for path in inputs if not Path(path).exists()]
    if missing:
        joined = "\n  ".join(missing)
        raise FileNotFoundError(f"Missing dataset inputs:\n  {joined}")

    command = [
        sys.executable,
        str(Path(__file__).with_name("prepare_dataset.py")),
        "--inputs",
        *inputs,
        "--output-dir",
        args.output_dir,
        "--validation-size",
        str(args.validation_size),
        "--test-size",
        str(args.test_size),
        "--dedupe-on",
        "code",
        "--require-def",
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
