# Инструкция пользователя и демонстрационный сценарий

## Назначение

`Python Docstring Generator` - расширение для Visual Studio Code, которое генерирует Python docstring с помощью локальной модели через Ollama.

Основной сценарий:

1. открыть Python-файл;
2. выделить ровно одну функцию или метод;
3. запустить генерацию;
4. посмотреть preview;
5. вставить docstring, заменить существующий docstring или сгенерировать другой вариант.

## Требования

На компьютере должны быть:

- Visual Studio Code `1.90.0` или новее;
- Ollama, установленная отдельно;
- доступ к интернету для первого скачивания модели;
- свободное место на диске для модели.

Рекомендуемая модель для демонстрации:

```text
qwen2.5-coder:1.5b
```

Расширение может:

- проверить доступность Ollama API;
- запустить `ollama serve`, если Ollama уже установлена и доступна в `PATH`;
- скачать выбранную модель через Ollama `/api/pull`;
- показать progress, status bar и понятные сообщения об ошибках.

Расширение не устанавливает само приложение Ollama в систему. Если Ollama не установлена, расширение предложит открыть страницу загрузки.

## Установка на другом ПК через VSIX

Передать на другой ПК нужно файл:

```text
vscode-extension/python-docstring-generator/release/python-docstring-generator-0.0.2.vsix
```

### Вариант 1: через интерфейс VS Code

1. Открыть VS Code.
2. Открыть Extensions.
3. Нажать `...` в правом верхнем углу панели Extensions.
4. Выбрать `Install from VSIX...`.
5. Указать файл `python-docstring-generator-0.0.2.vsix`.
6. Перезапустить VS Code.

### Вариант 2: через терминал

Перейти в папку с `.vsix` и выполнить:

```bash
code --install-extension python-docstring-generator-0.0.2.vsix
```

Если команда `code` недоступна в терминале, установку проще выполнить через интерфейс VS Code.

## Установка Ollama

Ollama устанавливается отдельно:

```text
https://ollama.com/download
```

После установки можно проверить доступность:

```bash
ollama --version
```

Модель можно скачать вручную:

```bash
ollama pull qwen2.5-coder:1.5b
```

Или доверить скачивание расширению через команду `Setup Local Environment`.

## Первый запуск после установки

1. Открыть VS Code.
2. Открыть Command Palette.
3. Запустить:

```text
Python Docstring Generator: Setup Local Environment
```

Команда выполняет подготовку:

- проверяет настройки extension;
- проверяет доступность Ollama API;
- пытается запустить `ollama serve` для localhost URL, если сервер не отвечает;
- проверяет наличие выбранной модели;
- скачивает модель, если она отсутствует и `autoPullModel` включен;
- показывает checklist и пишет диагностику в Output Channel.

Ожидаемый успешный checklist:

```text
[ok] VS Code extension loaded
[ok] Configuration valid
[ok] Ollama API reachable
[ok] Model available
[ok] Local generation ready
```

Пункт `Ollama startup` появляется только если расширению действительно пришлось запускать `ollama serve`.

## Настройки

Основные настройки:

- `pythonDocstringGenerator.ollamaUrl` - адрес Ollama API. По умолчанию `http://localhost:11434`.
- `pythonDocstringGenerator.model` - имя модели. По умолчанию `qwen2.5-coder:1.5b`.
- `pythonDocstringGenerator.temperature` - температура генерации от `0` до `2`. По умолчанию `0.2`.
- `pythonDocstringGenerator.numPredict` - максимум генерируемых токенов. По умолчанию `256`.
- `pythonDocstringGenerator.autoStartOllama` - автоматически запускать `ollama serve`, если возможно.
- `pythonDocstringGenerator.autoPullModel` - автоматически скачивать выбранную модель, если ее нет.

## Команды

Доступные команды в Command Palette:

- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Select Ollama Model`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

## Выбор модели

Команда:

```text
Python Docstring Generator: Select Ollama Model
```

Она получает список моделей из локального Ollama `/api/tags`, показывает Quick Pick и сохраняет выбранную модель в VS Code settings.

Если список пустой, сначала запустите `Setup Local Environment` или скачайте модель вручную:

```bash
ollama pull qwen2.5-coder:1.5b
```

## Status Bar

После запуска VS Code в status bar появляется индикатор:

```text
Docstring: ...
```

Возможные состояния:

- `Docstring: Ready` - Ollama доступен, модель установлена;
- `Docstring: Offline` - Ollama недоступен;
- `Docstring: Model missing` - сервер доступен, но выбранной модели нет;
- `Docstring: Downloading` - модель скачивается;
- `Docstring: Generating` - идет генерация docstring;
- `Docstring: Checking` - идет проверка состояния;
- `Docstring: Error` - произошла ошибка.

По клику на status bar открывается меню действий:

- Generate Docstring;
- Regenerate Docstring;
- Setup Local Environment;
- Select Ollama Model;
- Check Ollama Connection;
- Refresh Status;
- Show Output Channel;
- Open Settings.

## Генерация docstring

Пример кода:

```python
def add(a, b):
    return a + b
```

Шаги:

1. Выделить всю функцию.
2. Запустить `Python Docstring Generator: Generate Python Docstring`.
3. Дождаться проверки окружения и генерации.
4. Посмотреть preview.
5. Выбрать `Insert`, `Regenerate`, `Cancel` или `Show Output`.

Пример результата:

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

## Замена существующего docstring

Если функция уже содержит docstring:

```python
def add(a, b):
    """Old description."""
    return a + b
```

Расширение покажет предупреждение и предложит:

```text
Replace Existing Docstring
Cancel
```

При выборе `Replace Existing Docstring` новый docstring заменит старый.

## Проверка выделения

Расширение ожидает, что пользователь выделит ровно одну функцию или метод.

Поддерживается:

```python
def add(a, b):
    return a + b
```

```python
async def fetch_data(url):
    return await client.get(url)
```

```python
class Calculator:
    def multiply(self, a, b):
        return a * b
```

Если выделить две функции или функцию вместе с лишним исполняемым кодом, расширение не отправит такой фрагмент в модель и покажет предупреждение.

## Типичные ошибки

- `Ollama URL is empty` - не задан адрес Ollama.
- `Model name is empty` - не задано имя модели.
- `Ollama is not reachable` - сервер не запущен или URL неверный.
- `Model is not installed` - выбранная модель не найдена.
- `Request timed out` - Ollama или модель отвечают слишком долго.
- `The active editor is not a Python file` - открыт не Python-файл.
- `Select a Python function` - нет подходящего выделения.
- `Please select exactly one Python function or method` - выделено несколько функций или методов.
- `This function already appears to have a docstring` - docstring уже найден.

Технические детали доступны через Output Channel:

```text
Python Docstring Generator
```

## Запуск из исходного кода

Для разработки:

```bash
cd vscode-extension/python-docstring-generator
npm install
npm run compile
npm run lint
```

Запуск Extension Development Host:

1. открыть папку `vscode-extension/python-docstring-generator/` в VS Code;
2. нажать `F5`;
3. в новом окне VS Code проверить команды расширения.

Сборка `.vsix`:

```bash
npx --yes @vscode/vsce package --out release/python-docstring-generator-0.0.2.vsix
```

## Демонстрационный сценарий для защиты

1. Открыть VS Code с установленным extension.
2. Показать status bar indicator.
3. Запустить `Setup Local Environment`.
4. Показать checklist и Output Channel.
5. Запустить `Select Ollama Model` и показать, что модель выбирается из локального списка.
6. Открыть тестовый Python-файл.
7. Выделить простую функцию.
8. Запустить генерацию.
9. Показать `Docstring: Generating`.
10. Показать preview.
11. Нажать `Regenerate`.
12. Нажать `Insert`.
13. Показать функцию с новым docstring.
14. Показать замену существующего docstring.
15. Кратко объяснить, что код не отправлялся в cloud API.
