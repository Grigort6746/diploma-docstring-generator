# Контекст Для ChatGPT По Дипломному Проекту

Этот документ можно отправить в ChatGPT, чтобы писать пояснительную записку, введение, архитектурные разделы, описание реализации, тестирование и демонстрационные материалы по проекту.

## Тема Диплома

Официальная тема:

> Интеграция моделей машинного обучения для автоматизированной генерации документации в проектах на Python

## Краткое Описание

Проект представляет собой локальный инструмент для генерации Python docstring с помощью моделей машинного обучения. Основной пользовательский интерфейс - расширение для Visual Studio Code.

Пользователь выделяет Python-функцию в редакторе, расширение отправляет этот код в локальный Ollama REST API, локальная модель генерирует Google-style docstring, после чего пользователь просматривает результат и вставляет его в код.

Ключевой принцип: исходный код пользователя не отправляется в облачные API. Обработка выполняется локально.

## Репозиторий

Структура:

```text
diploma-docstring-generator/
├─ README.md
├─ docs/
│  ├─ PROJECT_OVERVIEW.md
│  ├─ USER_GUIDE.md
│  └─ CHATGPT_DIPLOMA_CONTEXT.md
├─ vscode-extension/
│  └─ python-docstring-generator/
│     ├─ package.json
│     ├─ README.md
│     ├─ tsconfig.json
│     └─ src/
│        └─ extension.ts
└─ training/
   ├─ README.md
   ├─ docstring_training_v2/
   ├─ pars/
   └─ legacy scripts and notebooks
```

## Основная Практическая Архитектура

```text
Python code selected in VS Code
-> VS Code extension written in TypeScript
-> local Ollama REST API
-> local code/documentation model
-> generated Google-style Python docstring
-> preview in VS Code
-> insertion into editor
```

## Почему Ollama

Ollama выбран как локальный inference backend, потому что:

- работает локально;
- предоставляет простой REST API;
- поддерживает разные модели;
- позволяет использовать lightweight model для демонстрации;
- не требует отправки пользовательского кода в облако.

## Модель

Расширение model-agnostic. Имя модели задаётся в настройках VS Code.

Текущая модель по умолчанию:

```text
qwen2.5-coder:1.5b
```

Рекомендуемые варианты для исследования:

- `qwen2.5-coder:1.5b` - лёгкая модель для стабильной демонстрации;
- `qwen2.5-coder:3b` - более качественный локальный вариант;
- fine-tuned Qwen2.5-Coder-7B - исследовательский/high-quality вариант, если доступен.

Проект не должен быть жёстко привязан только к Qwen2.5-Coder-7B.

## Реализованные Команды VS Code Extension

Command IDs:

```text
python-docstring-generator.generateDocstring
python-docstring-generator.regenerateDocstring
python-docstring-generator.checkOllamaConnection
python-docstring-generator.setupLocalEnvironment
python-docstring-generator.refreshStatus
python-docstring-generator.showOutput
python-docstring-generator.showStatusMenu
```

Пользовательские команды:

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

## Настройки VS Code Extension

Namespace:

```text
pythonDocstringGenerator
```

Settings:

```text
pythonDocstringGenerator.ollamaUrl
pythonDocstringGenerator.model
pythonDocstringGenerator.temperature
pythonDocstringGenerator.numPredict
pythonDocstringGenerator.autoStartOllama
pythonDocstringGenerator.autoPullModel
```

Defaults:

```text
ollamaUrl: http://localhost:11434
model: qwen2.5-coder:1.5b
temperature: 0.2
numPredict: 256
autoStartOllama: true
autoPullModel: true
```

## Текущие Возможности Extension

Расширение умеет:

- регистрировать команды VS Code;
- проверять Python-файл;
- читать выделенный код;
- валидировать настройки;
- проверять Ollama API;
- запускать `ollama serve`, если Ollama установлен, но не запущен;
- ждать запуска Ollama;
- проверять наличие модели через `/api/tags`;
- скачивать отсутствующую модель через `/api/pull`;
- отправлять запрос генерации в `/api/generate`;
- нормализовать ответ модели;
- удалять Markdown fences и лишние triple quotes;
- показывать preview перед вставкой;
- повторно генерировать docstring;
- вставлять docstring после строки `def` или `async def`;
- определять уже существующий docstring;
- показывать status bar indicator;
- открывать интерактивное меню из status bar;
- вести Output Channel `Python Docstring Generator`.

## Status Bar И UX

Status bar показывает состояния:

- `Docstring: Ready`
- `Docstring: Offline`
- `Docstring: Model missing`
- `Docstring: Downloading`
- `Docstring: Checking`
- `Docstring: Error`

По клику открывается Quick Pick меню:

- Generate Docstring;
- Regenerate Docstring;
- Setup Local Environment;
- Check Ollama Connection;
- Refresh Status;
- Show Output Channel;
- Open Settings.

## Setup Checklist

Команда setup показывает checklist:

```text
[ok] VS Code extension loaded
[ok] Configuration valid
[ok] Ollama API reachable
[ok] Ollama startup
[ok] Model available
[ok] Local generation ready
```

Это удобно для демонстрации на защите, потому что показывает, что инструмент самостоятельно диагностирует и подготавливает локальное окружение.

## Prompt

Prompt требует:

- сгенерировать только Python docstring;
- использовать Google-style;
- не использовать Markdown;
- не повторять исходный код;
- документировать все видимые аргументы;
- добавлять `Returns`, если функция возвращает значение;
- добавлять `Raises`, только если исключения явно видны в коде;
- не выдумывать поведение, которого нет в сигнатуре или теле функции;
- писать кратко, но информативно.

## Обработка Ошибок

Пользователь получает короткие понятные сообщения:

- Ollama не установлен;
- Ollama не запущен;
- неправильный URL;
- модель не установлена;
- модель скачивается;
- timeout;
- пустое выделение;
- не Python-файл;
- docstring уже существует;
- модель вернула пустой ответ.

Технические детали пишутся в Output Channel.

## Training Workspace

Папка:

```text
training/
```

Назначение:

- подготовка датасетов;
- сравнение датасетов;
- удаление исходных docstring из кода для предотвращения leakage;
- обучение CodeT5/T5 моделей;
- генерация примеров;
- исследовательские эксперименты.

Наиболее чистый pipeline:

```text
training/docstring_training_v2/
```

Большие датасеты, checkpoint-и и веса моделей не хранятся в Git.

## Что Важно Подчеркнуть В Пояснительной Записке

1. Ручное написание документации занимает время и часто откладывается.
2. Существующие AI-инструменты часто являются облачными и могут быть неприемлемы для приватного кода.
3. Проект предлагает локальный подход.
4. ML-модель интегрирована прямо в рабочий процесс разработчика.
5. VS Code extension демонстрирует практическую применимость.
6. Ollama позволяет заменить модель без переписывания extension.
7. Архитектура простая, воспроизводимая и пригодная для защиты.

## Возможная Структура Пояснительной Записки

1. Введение.
2. Анализ предметной области.
3. Обзор существующих подходов к генерации документации.
4. Обоснование выбора локальной архитектуры.
5. Обзор моделей code-to-text/code-to-docstring.
6. Проектирование системы.
7. Реализация VS Code extension.
8. Реализация локального inference через Ollama.
9. Подготовка и обучение моделей.
10. Тестирование и демонстрация.
11. Оценка результатов.
12. Заключение.

## Текущие Ограничения

- MVP требует ручного выделения функции.
- Основная поддержка - single-line `def` и `async def`.
- Decorators и multiline signatures требуют улучшения.
- Extension пока не заменяет существующий docstring, а предупреждает пользователя.
- Сам Ollama не устанавливается автоматически, но extension открывает страницу установки.

## Roadmap

Phase 1 - стабилизация MVP:

- локальная генерация;
- setup flow;
- preview;
- status bar;
- diagnostics.

Phase 2 - улучшение вставки:

- decorators;
- class methods;
- multiline signatures;
- replacement существующего docstring.

Phase 3 - refactor:

- `config.ts`;
- `ollamaClient.ts`;
- `prompt.ts`;
- `docstringInserter.ts`;
- `extension.ts`.

Phase 4 - tests:

- config validation;
- prompt generation;
- response normalization;
- insertion formatting;
- existing docstring detection.

Phase 5 - model quality:

- сравнение моделей;
- настройка prompt;
- подбор inference parameters;
- fine-tuning.

Phase 6 - защита:

- demo Python-файл;
- подготовленная модель;
- screenshots;
- fallback plan;
- описание setup steps.

## Последнее Состояние Разработки

На текущем этапе реализован рабочий интерактивный MVP:

- autonomous setup через Ollama;
- status bar;
- quick action menu;
- setup checklist;
- preview before insert;
- regenerate;
- detailed Output Channel;
- README и проектная документация.

Команды проверки:

```bash
cd vscode-extension/python-docstring-generator
npm run compile
npm run lint
```

Обе команды должны проходить успешно.
