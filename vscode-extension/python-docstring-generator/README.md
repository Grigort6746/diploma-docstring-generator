# Python Docstring Generator

VS Code extension prototype for generating Python docstrings locally with Ollama.

The extension sends selected Python code to a local Ollama server and inserts a generated Google-style docstring into the editor. Source code is processed locally and is not sent to cloud APIs.

## Requirements

- Visual Studio Code
- Ollama installed locally

The extension can start a local Ollama server and download the configured model automatically. If Ollama itself is not installed or not available in `PATH`, the extension shows a guided install message.

Recommended lightweight model for demonstration: `qwen2.5-coder:1.5b`

## Commands

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

## Extension Settings

This extension contributes the following settings:

- `pythonDocstringGenerator.ollamaUrl`: Ollama base URL. Default: `http://localhost:11434`
- `pythonDocstringGenerator.model`: Ollama model name. Default: `qwen2.5-coder:1.5b`
- `pythonDocstringGenerator.temperature`: Generation temperature from `0` to `2`. Default: `0.2`
- `pythonDocstringGenerator.numPredict`: Positive maximum generated token count. Default: `256`
- `pythonDocstringGenerator.autoStartOllama`: Try to start local `ollama serve` automatically. Default: `true`
- `pythonDocstringGenerator.autoPullModel`: Download the configured model if it is missing. Default: `true`

## Usage

1. Install Ollama if it is not installed yet.
2. Run `Python Docstring Generator: Setup Local Environment` once, or let the generate command prepare the model automatically.
3. Open a Python file in VS Code.
4. Select a complete Python function with a single-line `def` or `async def` signature.
5. Run `Python Docstring Generator: Generate Python Docstring`.

The extension checks for an existing docstring in the selected function and skips insertion if the first meaningful line after the function signature is already a triple-quoted string.

During setup, the extension:

- checks the configured Ollama URL;
- starts `ollama serve` for localhost URLs when possible;
- checks whether the configured model is installed;
- pulls the model through Ollama `/api/pull` if it is missing;
- reports progress and technical diagnostics in the `Python Docstring Generator` Output Channel.

## Interactive Demo Features

The extension includes a status bar indicator that shows the local generation state:

- `Docstring: Ready`
- `Docstring: Offline`
- `Docstring: Model missing`
- `Docstring: Downloading`

Click the status bar item to open a quick action menu for setup, connection checks, generation, status refresh, settings, and diagnostics.

The setup command writes a step-by-step checklist to the Output Channel and shows the checklist when the environment is ready.

Generated docstrings are previewed before insertion. From the preview dialog, you can:

- insert the generated docstring;
- regenerate another candidate;
- cancel insertion;
- open the Output Channel.

Example input:

```python
def add(a, b):
    return a + b
```

Example result:

```python
def add(a, b):
    """Add two values.

    Args:
        a: The first value.
        b: The second value.

    Returns:
        The sum of the two values.
    """
    return a + b
```

## MVP Limitations

The first version is intentionally simple. It focuses on ordinary single-line Python function signatures. Decorators, multiline signatures, advanced existing-docstring replacement, and broader Python syntax handling can be improved later.
