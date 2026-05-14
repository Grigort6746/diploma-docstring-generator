# Инструкция И Демонстрационный Сценарий

## Назначение

`Python Docstring Generator` - расширение для Visual Studio Code, которое генерирует Python docstring с помощью локальной модели через Ollama.

Основной сценарий:

1. открыть Python-файл;
2. выделить функцию;
3. запустить генерацию;
4. посмотреть preview;
5. вставить docstring или сгенерировать другой вариант.

## Требования

Минимально нужно:

- Visual Studio Code;
- установленный Ollama;
- доступ к интернету для первичного скачивания модели, если её ещё нет локально.

Расширение само может:

- запустить локальный Ollama server;
- скачать выбранную модель;
- проверить состояние локального backend;
- показать ошибки и успешные операции.

## Установка Расширения Для Теста

В режиме разработки:

1. Открыть папку:

```text
vscode-extension/python-docstring-generator/
```

2. Установить зависимости:

```bash
npm install
```

3. Запустить сборку:

```bash
npm run compile
```

4. Открыть Extension Development Host через VS Code.

Для будущей демонстрации можно подготовить `.vsix`, но публикация в Marketplace не требуется для текущего MVP.

## Настройки

Основные настройки extension:

- `pythonDocstringGenerator.ollamaUrl` - адрес Ollama API. По умолчанию `http://localhost:11434`.
- `pythonDocstringGenerator.model` - имя модели. По умолчанию `qwen2.5-coder:1.5b`.
- `pythonDocstringGenerator.temperature` - температура генерации. По умолчанию `0.2`.
- `pythonDocstringGenerator.numPredict` - максимум генерируемых токенов. По умолчанию `256`.
- `pythonDocstringGenerator.autoStartOllama` - автоматически запускать Ollama, если он установлен, но не запущен.
- `pythonDocstringGenerator.autoPullModel` - автоматически скачивать модель, если её нет.

## Команды

Доступные команды в Command Palette:

- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

## Status Bar

После запуска VS Code в status bar появляется индикатор:

- `Docstring: Ready` - Ollama доступен, модель установлена;
- `Docstring: Offline` - Ollama недоступен;
- `Docstring: Model missing` - сервер доступен, но выбранной модели нет;
- `Docstring: Downloading` - модель скачивается;
- `Docstring: Checking` - идёт проверка состояния.

По клику на status bar открывается меню действий:

- Generate Docstring;
- Regenerate Docstring;
- Setup Local Environment;
- Check Ollama Connection;
- Refresh Status;
- Show Output Channel;
- Open Settings.

## Setup Local Environment

Команда:

```text
Python Docstring Generator: Setup Local Environment
```

Она выполняет пошаговую подготовку:

```text
[ok] VS Code extension loaded
[ok] Configuration valid
[ok] Ollama API reachable
[ok] Ollama startup
[ok] Model available
[ok] Local generation ready
```

Если Ollama не запущен, расширение попробует выполнить:

```bash
ollama serve
```

Если модель отсутствует, расширение скачает её через Ollama API `/api/pull`.

Если Ollama не установлен или команда `ollama` недоступна в `PATH`, расширение покажет ошибку и предложит открыть страницу загрузки Ollama.

## Генерация Docstring

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
5. Выбрать:
   - `Insert`;
   - `Regenerate`;
   - `Cancel`;
   - `Show Output`.

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

## Ручные Сценарии Проверки

### Scenario 1: Ollama Установлен И Модель Есть

Ожидаемый результат:

- status bar показывает `Docstring: Ready`;
- `Check Ollama Connection` сообщает, что модель доступна;
- генерация работает без дополнительных действий.

### Scenario 2: Ollama Установлен, Но Не Запущен

Ожидаемый результат:

- setup пытается запустить `ollama serve`;
- после запуска показывает успешный checklist;
- status bar переходит в `Ready`.

### Scenario 3: Модель Не Скачана

Ожидаемый результат:

- setup показывает скачивание модели;
- после скачивания модель становится доступной;
- генерация работает.

### Scenario 4: Ollama Не Установлен

Ожидаемый результат:

- пользователь видит понятную ошибку;
- доступна кнопка открытия страницы загрузки Ollama.

### Scenario 5: Preview И Regenerate

Ожидаемый результат:

- после генерации появляется preview;
- `Regenerate` создаёт новый вариант;
- `Insert` вставляет docstring;
- `Cancel` ничего не меняет в файле.

## Демонстрационный Сценарий Для Защиты

Рекомендуемый порядок показа:

1. Открыть VS Code с установленным extension.
2. Показать status bar indicator.
3. Запустить `Setup Local Environment`.
4. Показать checklist и Output Channel.
5. Открыть тестовый Python-файл.
6. Выделить простую функцию.
7. Запустить генерацию.
8. Показать preview.
9. Нажать `Regenerate`, чтобы продемонстрировать интерактивность.
10. Нажать `Insert`.
11. Показать итоговый код с docstring.
12. Кратко объяснить, что код не отправлялся в cloud API.

## Типичные Ошибки И Сообщения

- `Ollama URL is empty` - не задан адрес Ollama.
- `Model name is empty` - не задано имя модели.
- `Ollama is not reachable` - сервер не запущен или URL неверный.
- `Model is not installed` - выбранная модель не найдена.
- `Request timed out` - Ollama или модель отвечают слишком долго.
- `The active editor is not a Python file` - открыт не Python-файл.
- `Select a Python function` - нет выделения.
- `This function already appears to have a docstring` - docstring уже найден.

## Ограничения

- MVP ориентирован на выделенную функцию;
- сложные multiline signatures пока ограничены;
- автоматическая установка самого Ollama не выполняется;
- качество docstring зависит от выбранной модели.
