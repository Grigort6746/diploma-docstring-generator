# Чек-лист тестирования расширения на другом ПК

## 1. Что передать на другой ПК

Основной файл для установки:

```text
vscode-extension/python-docstring-generator/release/python-docstring-generator-0.0.2.vsix
```

Дополнительно полезно передать:

- `docs/USER_GUIDE.md` - инструкция пользователя и демонстрационный сценарий;
- `docs/PROJECT_OVERVIEW.md` - описание проекта;
- `docs/CHATGPT_DIPLOMA_CONTEXT.md` - контекст для подготовки дипломных материалов.

## 2. Предварительные требования

На тестовом ПК должны быть:

- Visual Studio Code `1.90.0` или новее;
- Ollama, установленная отдельно;
- интернет для первого скачивания модели;
- свободное место на диске для модели.

Рекомендуемая модель:

```text
qwen2.5-coder:1.5b
```

Важно: расширение не устанавливает само приложение Ollama. Оно может запустить уже установленный `ollama serve` и скачать модель через Ollama API.

## 3. Установка VSIX

### Через интерфейс VS Code

1. Открыть VS Code.
2. Перейти в Extensions.
3. Нажать `...`.
4. Выбрать `Install from VSIX...`.
5. Указать файл:

```text
python-docstring-generator-0.0.2.vsix
```

6. Перезапустить VS Code.

### Через терминал

```bash
code --install-extension python-docstring-generator-0.0.2.vsix
```

## 4. Проверка команд и настроек

Проверить, что в Command Palette появились команды:

- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Select Ollama Model`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

Проверить, что в Settings видны настройки:

- `pythonDocstringGenerator.ollamaUrl`
- `pythonDocstringGenerator.model`
- `pythonDocstringGenerator.temperature`
- `pythonDocstringGenerator.numPredict`
- `pythonDocstringGenerator.autoStartOllama`
- `pythonDocstringGenerator.autoPullModel`

## 5. Проверка status bar

После запуска VS Code должен появиться индикатор:

```text
Docstring: ...
```

Проверить состояния:

- `Docstring: Ready`
- `Docstring: Offline`
- `Docstring: Model missing`
- `Docstring: Downloading`
- `Docstring: Generating`
- `Docstring: Checking`
- `Docstring: Error`

Проверить, что по клику открывается меню:

- Generate Docstring;
- Regenerate Docstring;
- Setup Local Environment;
- Select Ollama Model;
- Check Ollama Connection;
- Refresh Status;
- Show Output Channel;
- Open Settings.

## 6. Проверка Setup Local Environment

Запустить:

```text
Python Docstring Generator: Setup Local Environment
```

Ожидаемый успешный результат:

- настройки валидны;
- Ollama API доступен;
- Ollama запускается автоматически, если установлен, но не запущен;
- модель скачивается автоматически, если ее нет;
- появляется checklist;
- status bar показывает `Docstring: Ready`.

Ожидаемый checklist:

```text
[ok] VS Code extension loaded
[ok] Configuration valid
[ok] Ollama API reachable
[ok] Model available
[ok] Local generation ready
```

Если Ollama не установлена:

- появляется понятная ошибка;
- доступна кнопка `Open Ollama Download`;
- после установки Ollama нужно повторить setup.

## 7. Проверка выбора модели

Запустить:

```text
Python Docstring Generator: Select Ollama Model
```

Ожидаемый результат:

- расширение показывает список моделей из локального Ollama;
- текущая модель помечена как `Current model`;
- выбранная модель сохраняется в setting `pythonDocstringGenerator.model`;
- status bar остается в корректном состоянии.

Если моделей нет:

- появляется сообщение `No Ollama models are installed locally`;
- можно перейти к `Setup Local Environment`.

## 8. Генерация docstring для простой функции

Код:

```python
def add(a, b):
    return a + b
```

Шаги:

1. Выделить всю функцию.
2. Запустить `Generate Python Docstring`.
3. Дождаться preview.
4. Нажать `Insert`.

Ожидаемый результат:

```python
def add(a, b):
    """..."""
    return a + b
```

Docstring вставлен сразу после строки `def`.

## 9. Preview и Regenerate

На preview-окне проверить:

- `Insert` вставляет docstring;
- `Regenerate` генерирует новый вариант без изменения файла;
- `Cancel` ничего не меняет;
- `Show Output` открывает Output Channel.

## 10. Функция с type hints

Код:

```python
def calculate_total(price: float, quantity: int, discount: float = 0.0) -> float:
    total = price * quantity
    return total - (total * discount)
```

Ожидаемый результат:

- параметры задокументированы;
- есть секция `Returns`;
- отступы корректны.

## 11. Метод внутри класса

Код:

```python
class Calculator:
    def multiply(self, a, b):
        return a * b
```

Ожидаемый результат:

- docstring вставляется внутрь метода;
- отступ соответствует уровню метода.

## 12. Async function

Код:

```python
async def fetch_data(url: str) -> dict:
    response = await client.get(url)
    return response.json()
```

Ожидаемый результат:

- `async def` определяется корректно;
- docstring вставляется с правильным отступом.

## 13. Существующий docstring

Код:

```python
def add(a, b):
    """Add two values."""
    return a + b
```

Ожидаемый результат:

- появляется предупреждение `This function already appears to have a docstring`;
- доступен выбор `Replace Existing Docstring`;
- при подтверждении старый docstring заменяется новым;
- при отмене файл не меняется.

## 14. Проверка неправильного выделения

### Две функции

```python
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
```

Ожидаемый результат:

```text
Please select exactly one Python function or method.
```

### Функция плюс лишний код после нее

```python
def add(a, b):
    return a + b

print(add(1, 2))
```

Ожидаемый результат:

```text
Please select only the target function body, without code after the function.
```

## 15. Проверка ошибок

Проверить сценарии:

- пустое выделение;
- открыт не Python-файл;
- неверный `ollamaUrl`;
- пустое имя модели;
- несуществующая модель;
- Ollama выключен;
- Ollama не установлен;
- нет интернета при скачивании модели.

Ожидаемый результат:

- пользователь видит короткое понятное сообщение;
- raw stack trace не показывается пользователю;
- технические детали доступны через `Python Docstring Generator` Output Channel.

## 16. Критерии успешного теста

Расширение готово к демонстрации, если:

- `.vsix` устанавливается без ошибок;
- команды видны в Command Palette;
- настройки видны в Settings;
- status bar работает;
- setup checklist показывается;
- модель скачивается через Ollama;
- выбор модели работает;
- preview появляется перед вставкой;
- regenerate работает;
- новый docstring вставляется корректно;
- существующий docstring можно заменить;
- неправильное выделение не отправляется в модель;
- ошибки понятны пользователю;
- код не отправляется в cloud API.

## 17. Быстрый демонстрационный сценарий

1. Открыть VS Code.
2. Показать установленное расширение.
3. Показать status bar.
4. Запустить `Setup Local Environment`.
5. Показать checklist.
6. Запустить `Select Ollama Model`.
7. Открыть Python-файл.
8. Выделить функцию.
9. Запустить генерацию.
10. Показать `Docstring: Generating`.
11. Показать preview.
12. Нажать `Regenerate`.
13. Нажать `Insert`.
14. Показать вставленный docstring.
15. Показать замену существующего docstring.
16. Показать ошибку при выделении двух функций.
17. Открыть Output Channel и объяснить локальный Ollama backend.
