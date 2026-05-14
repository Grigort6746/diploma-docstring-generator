# Diploma Docstring Generator

Diploma project for local Python docstring generation with machine learning models.

The repository is organized as a single workspace with two practical parts:

- `vscode-extension/python-docstring-generator/` - VS Code extension that sends selected Python code to local Ollama and inserts a generated docstring.
- `training/` - training, dataset preparation, and research scripts for code-to-docstring models.

The main product path is local execution. User code should not be sent to cloud APIs.

## Current MVP

The extension works with local Ollama models and keeps the model name configurable through VS Code settings. The training folder contains the research pipeline and legacy experiments that can be used for diploma comparison and future fine-tuning work.

## Local Artifacts

Large datasets, virtual environments, model checkpoints, and downloaded model weights are intentionally not tracked in Git. Keep them locally or document where to download/regenerate them.
