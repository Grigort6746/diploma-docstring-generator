# Python Docstring Generator

VS Code extension для локальной генерации Python docstring через Ollama.

Расширение отправляет выделенную Python-функцию в локальный Ollama REST API, получает Google-style docstring, показывает preview и вставляет результат в редактор. Код пользователя не отправляется в cloud API.

## Требования

- Visual Studio Code `1.90.0` или новее.
- Ollama, установленная отдельно.
- Интернет для первого скачивания модели.

Рекомендуемая модель для демонстрации:

```text
qwen2.5-coder:1.5b
```

Важно: расширение не устанавливает само приложение Ollama. Оно может запустить уже установленный `ollama serve`, скачать выбранную модель через Ollama API и открыть страницу загрузки, если Ollama не найдена.

## Установка из VSIX

Файл пакета:

```text
python-docstring-generator-0.0.2.vsix
```

Через VS Code:

1. Открыть Extensions.
2. Нажать `...`.
3. Выбрать `Install from VSIX...`.
4. Указать `python-docstring-generator-0.0.2.vsix`.
5. Перезапустить VS Code.

Через терминал:

```bash
code --install-extension python-docstring-generator-0.0.2.vsix
```

После установки запустите:

```text
Python Docstring Generator: Setup Local Environment
```

## Команды

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Select Ollama Model`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

## Настройки

- `pythonDocstringGenerator.ollamaUrl`: адрес Ollama API. По умолчанию `http://localhost:11434`.
- `pythonDocstringGenerator.model`: имя модели Ollama. По умолчанию `qwen2.5-coder:1.5b`.
- `pythonDocstringGenerator.temperature`: температура генерации от `0` до `2`. По умолчанию `0.2`.
- `pythonDocstringGenerator.numPredict`: максимум генерируемых токенов. По умолчанию `256`.
- `pythonDocstringGenerator.autoStartOllama`: пытаться запускать локальный `ollama serve`. По умолчанию `true`.
- `pythonDocstringGenerator.autoPullModel`: скачивать выбранную модель, если ее нет. По умолчанию `true`.

## Использование

1. Установите Ollama, если она еще не установлена.
2. Запустите `Python Docstring Generator: Setup Local Environment`.
3. Откройте Python-файл.
4. Выделите ровно одну полную Python-функцию или метод с single-line `def` или `async def`.
5. Запустите `Python Docstring Generator: Generate Python Docstring`.
6. Проверьте preview.
7. Выберите `Insert`, `Replace`, `Regenerate` или `Cancel`.

Если функция уже содержит docstring, расширение предложит заменить его через `Replace Existing Docstring`.

Если выделено несколько функций или лишний исполняемый код вокруг функции, расширение покажет предупреждение и не отправит этот фрагмент в модель.

## Status Bar

Расширение показывает состояние локального backend в status bar:

- `Docstring: Ready`
- `Docstring: Offline`
- `Docstring: Model missing`
- `Docstring: Downloading`
- `Docstring: Generating`
- `Docstring: Checking`
- `Docstring: Error`

По клику открывается меню действий: setup, выбор модели, проверка соединения, генерация, обновление статуса, настройки и Output Channel.

## Пример

До:

```python
def add(a, b):
    return a + b
```

После:

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

## Ограничения MVP

- лучше всего поддерживаются single-line `def` и `async def`;
- multiline signatures пока ограничены;
- сложные nested functions и нестандартные случаи Python-синтаксиса требуют дальнейшей доработки;
- качество docstring зависит от выбранной локальной модели.
