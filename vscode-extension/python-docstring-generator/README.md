# Python Docstring Generator

VS Code extension prototype for generating Python docstrings locally with Ollama.

The extension sends selected Python code to a local Ollama server and inserts a generated Google-style docstring into the editor. Source code is processed locally and is not sent to cloud APIs.

## Requirements

- Visual Studio Code
- Ollama running locally
- A local code model installed in Ollama

Recommended lightweight model for demonstration:

```bash
ollama pull qwen2.5-coder:1.5b
```

## Commands

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`

## Extension Settings

This extension contributes the following settings:

- `pythonDocstringGenerator.ollamaUrl`: Ollama base URL. Default: `http://localhost:11434`
- `pythonDocstringGenerator.model`: Ollama model name. Default: `qwen2.5-coder:1.5b`
- `pythonDocstringGenerator.temperature`: Generation temperature. Default: `0.2`
- `pythonDocstringGenerator.numPredict`: Maximum generated tokens. Default: `256`

## Usage

1. Start Ollama.
2. Open a Python file in VS Code.
3. Select a complete Python function with a single-line `def` or `async def` signature.
4. Run `Python Docstring Generator: Generate Python Docstring`.

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
