# Чеклист Тестирования Расширения На Другом ПК

## 1. Что Передать На Другой ПК

Основной файл для установки:

```text
vscode-extension/python-docstring-generator/release/python-docstring-generator-0.0.1.vsix
```

Дополнительно полезно передать:

- `docs/USER_GUIDE.md` - инструкция пользователя и демонстрационный сценарий;
- `docs/PROJECT_OVERVIEW.md` - общее описание проекта;
- `docs/CHATGPT_DIPLOMA_CONTEXT.md` - контекст для подготовки пояснительной записки.

## 2. Предварительные Требования

На тестовом ПК должны быть:

- Visual Studio Code;
- Ollama;
- доступ к интернету для первого скачивания модели;
- свободное место на диске для модели.

Рекомендуемая модель по умолчанию:

```text
qwen2.5-coder:1.5b
```

Важно: расширение умеет запускать Ollama и скачивать модель, но не устанавливает само приложение Ollama в систему. Если Ollama не установлен, extension покажет кнопку открытия страницы загрузки.

## 3. Установка VSIX

Вариант через интерфейс VS Code:

1. Открыть VS Code.
2. Перейти в Extensions.
3. Нажать `...`.
4. Выбрать `Install from VSIX...`.
5. Указать файл:

```text
python-docstring-generator-0.0.1.vsix
```

Вариант через терминал:

```bash
code --install-extension python-docstring-generator-0.0.1.vsix
```

После установки перезапустить VS Code.

## 4. Базовая Проверка После Установки

Проверить, что в Command Palette появились команды:

- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

Проверить, что в Settings видны настройки:

- `pythonDocstringGenerator.ollamaUrl`
- `pythonDocstringGenerator.model`
- `pythonDocstringGenerator.temperature`
- `pythonDocstringGenerator.numPredict`
- `pythonDocstringGenerator.autoStartOllama`
- `pythonDocstringGenerator.autoPullModel`

## 5. Проверка Status Bar

После запуска VS Code должен появиться индикатор в status bar:

```text
Docstring: ...
```

Возможные состояния:

- `Docstring: Ready`
- `Docstring: Offline`
- `Docstring: Model missing`
- `Docstring: Downloading`
- `Docstring: Checking`
- `Docstring: Error`

Проверить, что по клику открывается меню действий:

- Generate Docstring;
- Regenerate Docstring;
- Setup Local Environment;
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

- Ollama API доступен;
- Ollama запускается автоматически, если был установлен, но не запущен;
- модель скачивается автоматически, если её нет;
- появляется checklist;
- status bar показывает `Docstring: Ready`.

Ожидаемый checklist:

```text
[ok] VS Code extension loaded
[ok] Configuration valid
[ok] Ollama API reachable
[ok] Ollama startup
[ok] Model available
[ok] Local generation ready
```

Если Ollama не установлен:

- должно появиться понятное сообщение;
- должна быть кнопка `Open Ollama Download`;
- после установки Ollama нужно повторить setup.

## 7. Проверка Генерации Docstring

Создать или открыть Python-файл:

```python
def add(a, b):
    return a + b
```

Шаги:

1. Выделить всю функцию.
2. Запустить `Python Docstring Generator: Generate Python Docstring`.
3. Дождаться генерации.
4. Проверить preview.
5. Нажать `Insert`.

Ожидаемый результат:

```python
def add(a, b):
    """..."""
    return a + b
```

Docstring должен быть вставлен сразу после строки `def`.

## 8. Проверка Preview И Regenerate

На preview-окне проверить кнопки:

- `Insert` - вставляет docstring;
- `Regenerate` - генерирует новый вариант;
- `Cancel` - не меняет файл;
- `Show Output` - открывает Output Channel.

Ожидаемый результат:

- при `Regenerate` старый preview не вставляется;
- при `Cancel` файл остаётся без изменений;
- при `Insert` docstring вставляется в функцию.

## 9. Проверка Функции С Type Hints

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

## 10. Проверка Метода Внутри Класса

Код:

```python
class Calculator:
    def multiply(self, a, b):
        return a * b
```

Ожидаемый результат:

- docstring вставляется внутрь метода;
- отступ соответствует уровню метода.

## 11. Проверка Async Function

Код:

```python
async def fetch_data(url: str) -> dict:
    response = await client.get(url)
    return response.json()
```

Ожидаемый результат:

- `async def` определяется корректно;
- docstring вставляется с правильным отступом.

## 12. Проверка Уже Существующего Docstring

Код:

```python
def add(a, b):
    """Add two values."""
    return a + b
```

Ожидаемый результат:

- второй docstring не вставляется;
- пользователь получает предупреждение.

## 13. Проверка Ошибок

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

- пользователь видит короткую понятную ошибку;
- технические детали доступны через `Python Docstring Generator` Output Channel.

## 14. Что Считать Успешным Тестом

Расширение считается готовым к демонстрации, если:

- `.vsix` устанавливается без ошибок;
- команды видны в Command Palette;
- настройки видны в Settings;
- status bar работает;
- setup checklist показывается;
- модель скачивается автоматически;
- preview появляется перед вставкой;
- regenerate работает;
- docstring корректно вставляется;
- ошибки понятны пользователю;
- код не отправляется в cloud API.

## 15. Быстрый Демонстрационный Сценарий

Для защиты:

1. Открыть VS Code.
2. Показать установленное расширение.
3. Показать status bar.
4. Запустить `Setup Local Environment`.
5. Показать checklist.
6. Открыть Python-файл.
7. Выделить функцию.
8. Запустить генерацию.
9. Показать preview.
10. Нажать `Regenerate`.
11. Нажать `Insert`.
12. Показать вставленный docstring.
13. Открыть Output Channel и показать локальный Ollama backend.
