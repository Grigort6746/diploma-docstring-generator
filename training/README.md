# Training Workspace

This folder contains the training and research side of the diploma project.

The files were consolidated from the previous local workspace:

```text
C:\Project\torch
```

## Structure

- `docstring_training_v2/` - the cleanest current pipeline for dataset preparation, comparison, CodeT5/T5 training, and generation.
- `pars/` - legacy GitHub dataset collection scripts.
- `irz/` - small experimental scripts.
- `*.ipynb`, `*.py`, `*.mmd`, `*.png`, `*.svg` - legacy experiments, diagrams, and research notes.

## Data And Models

Large files from the old workspace were not copied into Git:

- `*.parquet`, `*.arrow`, `*.csv`, `*.xlsx`
- virtual environments
- local model folders
- training checkpoints and run outputs

Keep these artifacts locally when needed. The root `.gitignore` is configured to keep them out of commits.

## GitHub Dataset Parsers

Legacy parser scripts no longer contain hardcoded GitHub tokens. Use environment variables instead:

```powershell
$env:GITHUB_TOKEN = "your-token"
```

or for token rotation:

```powershell
$env:GITHUB_TOKENS = "token-1,token-2"
```

Do not commit real tokens.
