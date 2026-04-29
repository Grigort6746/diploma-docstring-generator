# Project Instructions for Codex

## Project Overview

This repository contains a diploma project focused on integrating machine learning models into the process of automatic documentation generation for Python projects.

The final result should be a local developer tool that generates Python docstrings from selected Python code. The main user-facing component is a Visual Studio Code extension.

The project must prioritize:

- local execution;
- privacy;
- simplicity;
- reproducibility;
- demonstrability during the diploma defense.

The user’s source code must not be sent to cloud APIs.

---

## Official Diploma Topic

The official diploma topic is:

> Интеграция моделей машинного обучения для автоматизированной генерации документации в проектах на Python

The project must remain aligned with this topic.

---

## Main Goal

Build a working prototype of a VS Code extension that:

1. Works with Python files.
2. Allows the user to select a Python function.
3. Sends the selected code to a local model inference backend.
4. Receives a generated Google-style Python docstring.
5. Inserts the generated docstring into the editor.

The tool should be simple enough to explain in the diploma paper and stable enough to demonstrate during the defense.

---

## Current Architectural Direction

The current practical architecture is:

```text
Python code selected in VS Code
→ VS Code extension written in TypeScript
→ local Ollama REST API
→ local code/documentation model
→ generated Python docstring
→ insertion into the editor
```

The extension should be model-agnostic. It must not be hardcoded to one specific model.

The model name and Ollama API URL must be configurable through VS Code settings.

---

## Important Architectural Decision

Do not make the whole project depend only on Qwen2.5-Coder-7B.

Qwen2.5-Coder may be used as a research model and as a high-quality option, but the extension itself must support different local Ollama models.

The system should be described as a local docstring generation tool that can work with different models available in Ollama.

Recommended model options for testing:

```text
qwen2.5-coder:1.5b
qwen2.5-coder:3b
fine-tuned Qwen2.5-Coder-7B in GGUF format, if available
```

A lightweight model can be used for a stable demonstration. A larger fine-tuned model can be used for the research and comparison part of the diploma.

---

## Historical Context

Previously considered or partially implemented directions:

- CodeT5-small as a baseline model;
- Qwen2.5-Coder-7B-Instruct fine-tuned with QLoRA;
- GGUF conversion and quantization;
- Ollama integration;
- Transformers.js;
- a custom PyTorch Transformer for Russian docstrings.

The current practical implementation should focus on:

- VS Code extension;
- local Ollama API;
- configurable model name;
- local generation of Python docstrings.

Do not switch to cloud APIs.

Do not add unnecessary complex architecture unless explicitly requested.

---

## Current Development Priority

The immediate priority is to build the VS Code extension from scratch in a simple and reliable way.

The extension should initially implement:

1. Command registration.
2. Reading selected code from the active editor.
3. Checking that the active file is a Python file.
4. Reading configuration from VS Code settings.
5. Sending a request to Ollama.
6. Handling connection errors clearly.
7. Inserting the generated docstring into the editor.

The MVP should be developed incrementally. Each step must work before adding the next one.

---

## VS Code Extension Location

The extension is currently located in:

```text
vscode-extension/python-docstring-generator/
```

Main files:

```text
package.json
tsconfig.json
src/extension.ts
```

The extension must be written in TypeScript.

At the MVP stage, keep the implementation simple. Avoid unnecessary frameworks, bundlers, webviews, UI libraries, or complex abstractions.

---

## Expected VS Code Commands

The extension should provide at least the following commands.

### Generate Python Docstring

Command ID:

```text
python-docstring-generator.generateDocstring
```

Purpose:

- take selected Python code;
- generate a docstring using local Ollama;
- insert the generated docstring into the editor.

### Check Ollama Connection

Command ID:

```text
python-docstring-generator.checkOllamaConnection
```

Purpose:

- check whether the local Ollama server is available;
- show a clear success or error message to the user.

---

## Expected VS Code Settings

The extension should define settings in `package.json`.

Recommended settings:

```text
pythonDocstringGenerator.ollamaUrl
pythonDocstringGenerator.model
pythonDocstringGenerator.temperature
pythonDocstringGenerator.numPredict
```

Recommended default values:

```text
ollamaUrl: http://localhost:11434
model: qwen2.5-coder:1.5b
temperature: 0.2
numPredict: 256
```

Do not hardcode the model name or endpoint directly inside business logic.

---

## Ollama API

Use the local Ollama REST API.

Preferred endpoint:

```text
POST /api/generate
```

Typical request body:

```json
{
  "model": "qwen2.5-coder:1.5b",
  "prompt": "...",
  "stream": false,
  "options": {
    "temperature": 0.2,
    "num_predict": 256
  }
}
```

Typical response contains:

```json
{
  "response": "generated text"
}
```

The extension should handle common errors:

- Ollama is not running.
- The configured model is not installed.
- The selected code is empty.
- The active file is not a Python file.
- The model returns an empty response.
- The request fails or times out.

Use clear user-facing messages.

---

## Prompt Requirements

The prompt should ask the model to generate only a Python docstring.

The generated docstring should follow Google-style format.

The model should be instructed to:

- document all parameters;
- include `Returns` if the function returns a value;
- include `Raises` only if exceptions are evident from the code;
- not repeat the original code;
- not include Markdown formatting;
- return only the docstring content.

Recommended prompt structure:

```text
Generate a Google-style Python docstring for the following function.

Requirements:
- Return only the docstring.
- Do not include Markdown.
- Do not repeat the code.
- Document all arguments.
- Include Returns if the function returns a value.
- Include Raises only if the function clearly raises exceptions.

Python function:
<code here>
```

---

## Docstring Insertion Requirements

The extension should insert the generated docstring inside the selected function, directly after the function signature line.

Example input:

```python
def add(a, b):
    return a + b
```

Expected output:

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

Indentation must be handled carefully.

For the MVP, it is acceptable to support ordinary single-line function definitions first:

```python
def function_name(...):
```

More complex cases can be improved later:

- decorators;
- async functions;
- multiline signatures;
- class methods;
- nested functions;
- existing docstrings.

---

## Recommended Code Structure

At the first MVP stage, it is acceptable to keep everything in:

```text
src/extension.ts
```

Recommended internal structure:

- `activate`
- command registration
- `getConfiguration`
- `generatePrompt`
- `callOllama`
- `insertDocstring`
- `checkOllamaConnection`

After the MVP is stable, it is acceptable to split the code into modules:

```text
src/ollamaClient.ts
src/prompt.ts
src/docstringInserter.ts
src/extension.ts
```

Do not split prematurely.

---

## Coding Style

Use clear and simple TypeScript.

Prefer readable code over clever code.

Use small helper functions when they improve clarity.

Avoid over-engineering.

Avoid introducing additional dependencies unless there is a clear reason.

The extension should stay easy to explain in the diploma paper.

---

## Error Handling

The extension should show user-friendly messages through VS Code APIs:

```ts
vscode.window.showInformationMessage(...)
vscode.window.showWarningMessage(...)
vscode.window.showErrorMessage(...)
```

Do not show raw stack traces to the user.

Detailed technical information may be written to an Output Channel.

Recommended output channel name:

```text
Python Docstring Generator
```

---

## What Not To Do

Do not use cloud APIs as the main implementation path.

Do not send user code to external services.

Do not hardcode one model name in a way that prevents configuration.

Do not introduce a Python server unless explicitly requested.

Do not add a webview at the MVP stage.

Do not add unnecessary UI frameworks.

Do not replace Ollama with another backend unless explicitly requested.

Do not rewrite the whole architecture without explaining why.

Do not assume missing files. Inspect the actual project files before modifying them.

Do not make the extension depend only on Qwen2.5-Coder-7B.

---

## Diploma Writing Considerations

The implementation should be easy to describe in the diploma paper.

Important concepts to preserve:

- local inference;
- REST API interaction;
- VS Code integration;
- model comparison;
- configurable model backend;
- practical working prototype.

The project should support the following narrative:

1. Manual Python documentation is time-consuming.
2. Existing tools are often cloud-based or insufficiently adapted for local/private use.
3. The project studies ML models for code-to-docstring generation.
4. The system integrates local ML inference into the developer workflow.
5. The VS Code extension demonstrates practical applicability.

---

## Development Philosophy

Build incrementally.

Each step should be working before adding the next one.

Preferred development order:

1. Make the command appear in VS Code.
2. Read selected Python code.
3. Show selected code in Output Channel.
4. Add VS Code settings.
5. Add Ollama connection check.
6. Send selected code to Ollama.
7. Display generated docstring.
8. Insert docstring into editor.
9. Improve indentation.
10. Improve README and diploma documentation.

Stability is more important than feature count.

The MVP must be simple, understandable, and demonstrable.
