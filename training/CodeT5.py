"""
train_codet5.py
====================
Обучение модели CodeT5 для генерации документации к Python-коду.

Требования к датасету (.parquet):
-------------------------------------
Формат — Parquet (.parquet)
Обязательные колонки:
    - 'code'        — текст функции / класса / фрагмента Python-кода
    - 'docstring'   — текстовое описание (строка документации)
Все другие колонки будут автоматически удалены

Пример структуры:
| code                                | docstring                        |
|------------------------------------|----------------------------------|
| "def add(a,b): return a+b"         | "Возвращает сумму двух чисел."   |
| "def factorial(n): ..."            | "Вычисляет факториал числа n."   |

"""

import os
import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
import evaluate
import numpy as np
import torch
from transformers import RobertaTokenizer, T5ForConditionalGeneration, T5Config

import matplotlib.pyplot as plt
import json


# === 1. Загрузка и проверка датасета ===
def load_local_dataset(data_path: str) -> Dataset:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"❌ Файл не найден: {data_path}")

    print(f"🔹 Загружаем датасет из {data_path}")
    df = pd.read_parquet(data_path)
    print(f"📦 Загружено {len(df)} строк, колонки: {list(df.columns)}")

    # Проверка и фильтрация
    required_cols = {"code", "docstring"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"❌ В датасете должны быть колонки {required_cols}, найдено: {set(df.columns)}"
        )

    # Оставляем только нужные колонки
    df = df[list(required_cols)]

    # Удаляем пустые значения и строки
    df = df.dropna(subset=["code", "docstring"])
    df = df[df["code"].str.strip() != ""]
    df = df[df["docstring"].str.strip() != ""]

    print(f"✅ После фильтрации осталось {len(df)} примеров")

    return Dataset.from_pandas(df)


# === 2. Токенизация ===
def preprocess_function(examples, tokenizer):
    inputs = [
        "Создай docstring для следующей функции Python:\n" + code
        for code in examples["code"]
    ]
    targets = examples["docstring"]
    model_inputs = tokenizer(
        inputs, max_length=256, truncation=True, padding="max_length"
    )
    labels = tokenizer(
        targets, max_length=64, truncation=True, padding="max_length"
    )
    model_inputs["labels"] = labels["input_ids"]

    return model_inputs


# === 3. Функция для обучения ===
def train_model(data_path: str):
    ds = load_local_dataset(data_path)

    torch.set_num_threads(32)

    # Разделение на train/test
    split_ds = ds.train_test_split(test_size=0.1, seed=42)
    dataset = DatasetDict({
        "train": split_ds["train"],
        "test": split_ds["test"]
    })

    print("🔹 Загружаем локальный токенизатор и модель из local-codet5-small...")

    model_path = "local-codet5-small"

    # Загружаем токенизатор и модель локально
    tokenizer = RobertaTokenizer.from_pretrained(model_path)
    config = T5Config.from_pretrained(model_path)
    model = T5ForConditionalGeneration.from_pretrained(model_path, config=config)

    print("✅ Модель и токенизатор успешно загружены локально.")
    # Проверяем GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"💻 Используется устройство: {device}")
    if device == "cuda":
        gpu = torch.cuda.get_device_properties(0)
        total_gb = gpu.total_memory / 1024**3
        print(f"✅ GPU: {gpu.name} | CUDA: {torch.version.cuda} | VRAM: {total_gb:.1f} GB")
    else:
        print("⚠️ CUDA недоступна. Проверьте, что установлен torch с CUDA, например torch==2.9.0+cu126.")
    model.to(device)

    # Токенизация
    print("🔄 Токенизация датасета...")
    tokenized_ds = dataset.map(
        lambda x: preprocess_function(x, tokenizer),
        batched=True,
        remove_columns=dataset["train"].column_names,
    )


    # Загружаем метрики
    bleu = evaluate.load("bleu")
    rouge = evaluate.load("rouge")

    def compute_metrics(eval_preds):
        preds, labels = eval_preds

        # Раскодируем токены в текст
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

        # Убираем пробелы и пустые строки
        decoded_preds = [p.strip() for p in decoded_preds]
        decoded_labels = [l.strip() for l in decoded_labels]

        # BLEU
        bleu_result = bleu.compute(predictions=decoded_preds, references=[[l] for l in decoded_labels])

        # ROUGE
        rouge_result = rouge.compute(predictions=decoded_preds, references=decoded_labels)

        result = {
        "bleu": bleu_result["bleu"],
        "rouge1": rouge_result["rouge1"],
        "rougeL": rouge_result["rougeL"],
    }

        result = {k: round(v * 100, 2) for k, v in result.items()}
        return result



    # Параметры обучения
    training_args = Seq2SeqTrainingArguments(
        output_dir="./git_results",
        evaluation_strategy="epoch",
        save_strategy="epoch",
        learning_rate=5e-5,
        per_device_train_batch_size=6,
        per_device_eval_batch_size=6,
        num_train_epochs=6,
        weight_decay=0.01,
        predict_with_generate=True,
        logging_dir="./logs",
        logging_steps=100,
        save_total_limit=4,
        report_to="none",
    )

    # Trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset = tokenized_ds["train"],
        eval_dataset = tokenized_ds["test"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    # Обучение
    print("🚀 Начало обучения...")
    trainer.train()

    # Сохранение
    save_dir = "./git_model"
    trainer.save_model(save_dir)
    tokenizer.save_pretrained(save_dir)
    print(f"✅ Модель сохранена в {save_dir}")

    return tokenizer, model


# === 4. Функция тестирования модели ===
def test_model(tokenizer, model):
    print("\n🔎 Тестирование модели: введите Python-код для генерации docstring.")
    print("Введите 'exit' для выхода.\n")

    while True:
        code_snippet = input("💬 Введите код: ")
        if code_snippet.strip().lower() == "exit":
            break

        inputs = tokenizer(
            code_snippet,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256,
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(**inputs, max_length=64, num_beams=5)

        docstring = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"📘 Сгенерированный docstring:\n{docstring}\n")


# === 5. Запуск ===
if __name__ == "__main__":
    DATA_PATH = "git_dataset.parquet"

    tokenizer, model = train_model(DATA_PATH)
    test_model(tokenizer, model)
