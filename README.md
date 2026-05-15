# Diploma Docstring Generator

Дипломный проект на тему:

> Интеграция моделей машинного обучения для автоматизированной генерации документации в проектах на Python

Цель проекта - разработать локальный инструмент, который помогает генерировать Python docstring прямо в Visual Studio Code с использованием локальных моделей машинного обучения.

Код пользователя не отправляется в облачные API. Основной сценарий работает через локальный Ollama REST API.

## Текущий результат

В репозитории есть рабочий MVP VS Code extension `Python Docstring Generator`.

Расширение умеет:

- проверять локальный Ollama backend;
- запускать установленный Ollama server для localhost-сценария;
- скачивать выбранную модель через Ollama `/api/pull`;
- выбирать модель из списка локально установленных Ollama models;
- генерировать Google-style docstring для выделенной Python-функции;
- проверять, что выделена ровно одна функция или метод;
- показывать preview перед вставкой;
- повторно генерировать вариант docstring;
- заменять уже существующий docstring по подтверждению пользователя;
- показывать состояние в status bar;
- писать техническую диагностику в Output Channel.

Актуальная версия расширения: `0.0.2`.

## Структура репозитория

- `vscode-extension/python-docstring-generator/` - VS Code extension, основной демонстрационный продукт.
- `vscode-extension/python-docstring-generator/release/` - локальные `.vsix` пакеты для тестовой установки. Папка не коммитится в Git.
- `training/` - исследовательские и обучающие скрипты, датасеты/пайплайны и эксперименты.
- `docs/` - проектная документация, пользовательская инструкция, чек-лист тестирования и контекст для подготовки дипломных материалов.

## Быстрый запуск на другом ПК

Нужно передать файл:

```text
vscode-extension/python-docstring-generator/release/python-docstring-generator-0.0.2.vsix
```

На другом ПК должны быть:

- Visual Studio Code `1.90.0` или новее;
- Ollama, установленная отдельно;
- доступ к интернету для первого скачивания модели;
- свободное место на диске для модели.

Установка через интерфейс VS Code:

1. Открыть VS Code.
2. Открыть Extensions.
3. Нажать `...`.
4. Выбрать `Install from VSIX...`.
5. Указать `python-docstring-generator-0.0.2.vsix`.
6. Перезапустить VS Code.

Установка через терминал:

```bash
code --install-extension python-docstring-generator-0.0.2.vsix
```

После установки:

1. Открыть Python-файл.
2. Запустить команду `Python Docstring Generator: Setup Local Environment`.
3. Дождаться проверки Ollama и скачивания модели, если ее еще нет.
4. Выделить ровно одну Python-функцию или метод.
5. Запустить `Python Docstring Generator: Generate Python Docstring`.

Важно: расширение не устанавливает само приложение Ollama в систему. Оно может открыть страницу загрузки Ollama, запустить уже установленный `ollama serve` и скачать выбранную модель через локальный Ollama API.

## Рекомендуемая модель

Для стабильной демонстрации:

```text
qwen2.5-coder:1.5b
```

Также можно тестировать:

```text
qwen2.5-coder:3b
```

Fine-tuned Qwen2.5-Coder-7B лучше рассматривать как исследовательский/high-quality вариант, а не как единственный вариант демонстрации.

## Документация

- [Описание проекта](docs/PROJECT_OVERVIEW.md)
- [Инструкция пользователя и демонстрационный сценарий](docs/USER_GUIDE.md)
- [Чек-лист тестирования расширения](docs/EXTENSION_TEST_CHECKLIST.md)
- [Контекст для подготовки дипломных материалов](docs/CHATGPT_DIPLOMA_CONTEXT.md)

## Разработка расширения

```bash
cd vscode-extension/python-docstring-generator
npm install
npm run compile
npm run lint
```

Запуск в Extension Development Host выполняется из VS Code через `F5`.

Сборка `.vsix`:

```bash
cd vscode-extension/python-docstring-generator
npx --yes @vscode/vsce package --out release/python-docstring-generator-0.0.2.vsix
```

## Локальные артефакты

Большие датасеты, виртуальные окружения, checkpoint-файлы, веса моделей и `.vsix` пакеты не хранятся в Git. Они должны оставаться локально или восстанавливаться по инструкции.
