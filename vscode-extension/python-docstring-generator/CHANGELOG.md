# Change Log

All notable changes to the `python-docstring-generator` extension are documented here.

## [0.0.2]

- Added validation that the selection contains exactly one Python function or method.
- Added protection against sending surrounding executable code to the model.
- Added replacement flow for existing docstrings.
- Added `Select Ollama Model` command based on local Ollama `/api/tags`.
- Added `Docstring: Generating` status bar state.
- Improved setup, generation progress, status refresh and README instructions.

## [0.0.1]

- Initial MVP release.
- Added local Ollama generation through `/api/generate`.
- Added Ollama connection check through `/api/tags`.
- Added configurable Ollama URL, model, temperature and token limit.
- Added preview, regenerate, status bar, setup checklist and Output Channel diagnostics.
