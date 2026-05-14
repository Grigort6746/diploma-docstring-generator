# Docstring Training V2

Clean pipeline for training a Python code-to-docstring model.

The folder is intentionally separate from the older experiments. It can:

- normalize datasets from parquet/csv/json/jsonl/xlsx
- remove source docstrings from code to prevent leakage
- deduplicate examples across datasets
- split train/validation/test by repository when repo metadata exists
- compare a new dataset against the existing project datasets
- fine-tune CodeT5/T5 models
- run inference with the same prompt used during training

## 1. Compare a new dataset

Put your new dataset anywhere in the project, then run:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\compare_datasets.py --candidate path\to\my_50k_dataset.parquet
```

By default it compares against:

- `git_dataset.parquet`
- `finaly_dataset.parquet`
- `functions_with_docstrings_4.parquet`
- `functions_with_docstrings_2.parquet`
- `new_dataset.parquet`

To write a merged raw parquet at the same time:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\compare_datasets.py `
  --candidate path\to\my_50k_dataset.parquet `
  --merged-output docstring_training_v2\data\merged_raw.parquet
```

## 2. Prepare train/validation/test files

Use only the new dataset:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\prepare_dataset.py `
  --inputs path\to\my_50k_dataset.parquet `
  --output-dir docstring_training_v2\data\my_50k
```

Use the new dataset plus current project datasets:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\prepare_dataset.py `
  --inputs path\to\my_50k_dataset.parquet git_dataset.parquet finaly_dataset.parquet `
  --output-dir docstring_training_v2\data\merged
```

Outputs:

- `dataset_full.parquet` with metadata for auditing and future merging
- `train.parquet` with only `code` and `docstring`
- `validation.parquet` with only `code` and `docstring`
- `test.parquet` with only `code` and `docstring`
- `dataset_report.json`

To rebuild the largest known local dataset in this project:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\build_max_dataset.py
```

To include another freshly collected dataset:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\build_max_dataset.py `
  --extra-inputs path\to\new_dataset.parquet
```

## 3. Train

Start with the local CodeT5-small checkpoint:

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\train.py `
  --data-dir docstring_training_v2\data\merged `
  --model-path local-codet5-small `
  --output-dir docstring_training_v2\runs\codet5_small_merged `
  --batch-size 8 `
  --gradient-accumulation-steps 2 `
  --max-source-length 512 `
  --max-target-length 160 `
  --epochs 4
```

If CUDA runs out of memory, lower `--batch-size` to `2`.

After training, the run directory contains:

- `metrics.json`
- `training_log.csv`
- `plots/loss_curves.png`
- `plots/quality_metrics.png`
- `plots/learning_rate.png`
- `final/`

The training script uses the same prompt for training and inference:

```text
Generate a Python docstring:
```

## 4. Generate

```powershell
.\.venv\Scripts\python.exe docstring_training_v2\generate.py `
  --model-dir docstring_training_v2\runs\codet5_small_merged\final `
  --code-file path\to\function.py
```

## Dataset expectations

The scripts auto-detect common column names.

Code columns:

- `code`
- `source`
- `source_code`
- `original_string`
- `func_code`

Docstring columns:

- `docstring`
- `doc`
- `documentation`
- `summary`
- `comment`

Repository grouping columns:

- `repo_url`
- `repo`
- `repository`
- `project`

If auto-detection is wrong, pass `--code-column` and `--doc-column`.
