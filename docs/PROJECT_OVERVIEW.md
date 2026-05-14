# Описание Проекта

## Тема

Официальная тема дипломного проекта:

> Интеграция моделей машинного обучения для автоматизированной генерации документации в проектах на Python

Проект исследует и демонстрирует практическое применение моделей машинного обучения для автоматической генерации документации к Python-коду.

## Цель

Создать локальный инструмент для разработчика, который:

- работает внутри Visual Studio Code;
- принимает выделенную Python-функцию;
- использует локальную ML-модель через Ollama;
- генерирует Google-style Python docstring;
- позволяет просмотреть результат перед вставкой;
- вставляет docstring обратно в код.

Главный акцент проекта - локальность, приватность, воспроизводимость и пригодность для демонстрации на защите.

## Пользовательский Сценарий

```text
Пользователь выделяет Python-функцию в VS Code
-> VS Code extension получает выделенный код
-> extension проверяет локальное окружение Ollama
-> при необходимости запускает Ollama и скачивает модель
-> extension отправляет prompt в локальный Ollama REST API
-> локальная модель генерирует Google-style docstring
-> extension показывает preview
-> пользователь вставляет, регенерирует или отменяет результат
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

## Основные Компоненты

### VS Code Extension

Путь:

```text
vscode-extension/python-docstring-generator/
```

Главные файлы:

- `package.json` - команды, настройки и metadata расширения;
- `src/extension.ts` - основная логика MVP;
- `README.md` - инструкция по использованию extension.

Extension реализован на TypeScript без webview, React, bundler и лишних зависимостей. Это сделано специально, чтобы MVP оставался простым и объяснимым в дипломной работе.

### Training Workspace

Путь:

```text
training/
```

Содержит:

- подготовку и сравнение датасетов;
- CodeT5/T5 training pipeline;
- генерацию примеров;
- legacy-эксперименты;
- вспомогательные скрипты и ноутбуки.

Наиболее чистая текущая обучающая часть:

```text
training/docstring_training_v2/
```

## Функции Расширения

Текущие команды:

- `Python Docstring Generator: Generate Python Docstring`
- `Python Docstring Generator: Regenerate Python Docstring`
- `Python Docstring Generator: Check Ollama Connection`
- `Python Docstring Generator: Setup Local Environment`
- `Python Docstring Generator: Refresh Local Model Status`
- `Python Docstring Generator: Show Output Channel`

Настройки:

- `pythonDocstringGenerator.ollamaUrl`
- `pythonDocstringGenerator.model`
- `pythonDocstringGenerator.temperature`
- `pythonDocstringGenerator.numPredict`
- `pythonDocstringGenerator.autoStartOllama`
- `pythonDocstringGenerator.autoPullModel`

## Автономность

Расширение может автоматически:

- проверить доступность Ollama API;
- запустить `ollama serve`, если Ollama установлен, но не запущен;
- проверить наличие выбранной модели;
- скачать модель через `/api/pull`, если её нет;
- показать progress и статус пользователю;
- вести подробную диагностику в Output Channel.

Расширение не устанавливает само приложение Ollama silently. Если Ollama не найден в `PATH`, пользователь получает понятное сообщение и кнопку для открытия страницы загрузки Ollama.

## Приватность

Проект не использует cloud API как основной backend.

Код пользователя обрабатывается локально:

- внутри VS Code;
- локальным Ollama сервером;
- локально установленной моделью.

Это важно для проектов, где нельзя отправлять исходный код во внешние сервисы.

## Текущие Ограничения MVP

- требуется выделить функцию вручную;
- лучше всего поддерживаются однострочные `def` и `async def`;
- multiline signatures пока не являются основной целью;
- decorators и сложные случаи Python-синтаксиса требуют дальнейшего улучшения;
- полноценный Python parser пока не используется;
- установка самого Ollama остаётся guided step, а не silent install.

## Дальнейшее Развитие

Рекомендуемый roadmap:

1. Улучшить insertion logic: decorators, multiline signatures, methods, existing docstring replacement.
2. Разделить `src/extension.ts` на модули после стабилизации UX.
3. Добавить unit tests для prompt, config validation, docstring normalization и insertion formatting.
4. Сравнить локальные модели: `qwen2.5-coder:1.5b`, `qwen2.5-coder:3b`, fine-tuned Qwen2.5-Coder-7B.
5. Подготовить стабильный demo pack для защиты: тестовый Python-файл, screenshots, setup steps, fallback plan.
