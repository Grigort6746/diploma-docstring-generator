# Описание проекта

## Тема

Официальная тема дипломного проекта:

> Интеграция моделей машинного обучения для автоматизированной генерации документации в проектах на Python

Проект демонстрирует практическое применение локальных моделей машинного обучения для генерации документации к Python-коду.

## Цель

Создать локальный инструмент для разработчика, который:

- работает внутри Visual Studio Code;
- принимает выделенную Python-функцию или метод;
- использует локальную ML-модель через Ollama;
- генерирует Google-style Python docstring;
- показывает preview результата;
- вставляет новый docstring или заменяет существующий;
- не отправляет пользовательский код во внешние сервисы.

## Пользовательский сценарий

```text
Пользователь открывает Python-файл в VS Code
-> выделяет ровно одну функцию или метод
-> запускает команду Generate Python Docstring
-> расширение проверяет выделение и локальное окружение
-> при необходимости запускает Ollama и скачивает модель
-> расширение отправляет prompt в локальный Ollama REST API
-> локальная модель генерирует docstring
-> расширение показывает preview
-> пользователь вставляет, заменяет, регенерирует или отменяет результат
```

## Архитектура

```text
Visual Studio Code
  |
  | selected Python code
  v
VS Code Extension (TypeScript)
  |
  | HTTP REST request
  v
Local Ollama API
  |
  | local model inference
  v
Ollama model, e.g. qwen2.5-coder:1.5b
  |
  | generated text
  v
Docstring preview and insertion in VS Code
```

Расширение model-agnostic: имя модели задается через VS Code settings и может быть выбрано из списка локально установленных моделей Ollama.

## Основные компоненты

### VS Code Extension

Путь:

```text
vscode-extension/python-docstring-generator/
```

Главные файлы:

- `package.json` - команды, настройки, metadata расширения;
- `src/extension.ts` - основная логика MVP;
- `README.md` - инструкция внутри пакета расширения;
- `release/*.vsix` - локально собранные пакеты для установки на другом ПК.

Extension реализован на TypeScript без webview, React, bundler и лишних runtime-зависимостей. Это сохраняет MVP простым для объяснения в дипломной работе.

### Training Workspace

Путь:

```text
training/
```

Содержит исследовательские материалы:

- подготовку и сравнение датасетов;
- CodeT5/T5 training pipeline;
- генерацию примеров;
- legacy-эксперименты;
- вспомогательные скрипты и ноутбуки.

Наиболее актуальная обучающая часть:

```text
training/docstring_training_v2/
```

## Возможности текущей версии

Текущая версия расширения: `0.0.2`.

Команды:

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Select Ollama Model`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

Настройки:

- `pythonDocstringGenerator.ollamaUrl`
- `pythonDocstringGenerator.model`
- `pythonDocstringGenerator.temperature`
- `pythonDocstringGenerator.numPredict`
- `pythonDocstringGenerator.autoStartOllama`
- `pythonDocstringGenerator.autoPullModel`

Поддержанные сценарии:

- генерация docstring для выделенной функции;
- генерация для `async def`;
- генерация для метода внутри класса;
- проверка, что выделена ровно одна функция или метод;
- предупреждение при лишнем коде в выделении;
- preview перед вставкой;
- regenerate;
- замена существующего docstring;
- выбор модели из локального списка Ollama;
- status bar с состояниями `Ready`, `Offline`, `Model missing`, `Downloading`, `Generating`, `Error`;
- Output Channel для технической диагностики.

## Установка и автономность

Расширение устанавливается через `.vsix`:

```text
vscode-extension/python-docstring-generator/release/python-docstring-generator-0.0.2.vsix
```

Важно разделять три вещи:

1. **VS Code extension** устанавливается из `.vsix`.
2. **Ollama application** устанавливается пользователем отдельно.
3. **Ollama model** может быть скачана расширением автоматически через `/api/pull`, если Ollama уже установлен и доступен.

Расширение не выполняет silent-install самого приложения Ollama. Если Ollama не найдена, пользователь получает понятное сообщение и кнопку открытия страницы загрузки.

## Приватность

Проект не использует cloud API как основной backend.

Код пользователя обрабатывается локально:

- внутри VS Code;
- локальным Ollama server;
- локально установленной моделью.

Это важно для проектов, где нельзя отправлять исходный код во внешние сервисы.

## Ограничения MVP

- требуется вручную выделить функцию или метод;
- лучше всего поддерживаются single-line `def` и `async def`;
- multiline signatures пока не являются основным сценарием;
- сложные nested functions и нестандартные случаи Python-синтаксиса требуют дальнейшей доработки;
- полноценный Python parser пока не используется;
- качество docstring зависит от выбранной модели;
- установка самого приложения Ollama остается guided step, а не полностью автоматическим системным установщиком.

## Дальнейшее развитие

Рекомендуемый roadmap:

1. Улучшить поддержку decorators, multiline signatures и сложных class/nested cases.
2. Добавить unit tests для prompt, config validation, normalization, selection analysis и insertion formatting.
3. Разделить `src/extension.ts` на модули после стабилизации UX.
4. Сравнить локальные модели: `qwen2.5-coder:1.5b`, `qwen2.5-coder:3b`, fine-tuned Qwen2.5-Coder-7B.
5. Подготовить стабильный demo pack для защиты: тестовый Python-файл, setup steps, screenshots, fallback plan.
