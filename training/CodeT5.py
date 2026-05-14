"""
train_codet5.py
====================
РћР±СѓС‡РµРЅРёРµ РјРѕРґРµР»Рё CodeT5 РґР»СЏ РіРµРЅРµСЂР°С†РёРё РґРѕРєСѓРјРµРЅС‚Р°С†РёРё Рє Python-РєРѕРґСѓ.

РўСЂРµР±РѕРІР°РЅРёСЏ Рє РґР°С‚Р°СЃРµС‚Сѓ (.parquet):
-------------------------------------
Р¤РѕСЂРјР°С‚ вЂ” Parquet (.parquet)
РћР±СЏР·Р°С‚РµР»СЊРЅС‹Рµ РєРѕР»РѕРЅРєРё:
    - 'code'        вЂ” С‚РµРєСЃС‚ С„СѓРЅРєС†РёРё / РєР»Р°СЃСЃР° / С„СЂР°РіРјРµРЅС‚Р° Python-РєРѕРґР°
    - 'docstring'   вЂ” С‚РµРєСЃС‚РѕРІРѕРµ РѕРїРёСЃР°РЅРёРµ (СЃС‚СЂРѕРєР° РґРѕРєСѓРјРµРЅС‚Р°С†РёРё)
Р’СЃРµ РґСЂСѓРіРёРµ РєРѕР»РѕРЅРєРё Р±СѓРґСѓС‚ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРё СѓРґР°Р»РµРЅС‹

РџСЂРёРјРµСЂ СЃС‚СЂСѓРєС‚СѓСЂС‹:
| code                                | docstring                        |
|------------------------------------|----------------------------------|
| "def add(a,b): return a+b"         | "Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃСѓРјРјСѓ РґРІСѓС… С‡РёСЃРµР»."   |
| "def factorial(n): ..."            | "Р’С‹С‡РёСЃР»СЏРµС‚ С„Р°РєС‚РѕСЂРёР°Р» С‡РёСЃР»Р° n."   |

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


# === 1. Р—Р°РіСЂСѓР·РєР° Рё РїСЂРѕРІРµСЂРєР° РґР°С‚Р°СЃРµС‚Р° ===
def load_local_dataset(data_path: str) -> Dataset:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"вќЊ Р¤Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ: {data_path}")

    print(f"рџ”№ Р—Р°РіСЂСѓР¶Р°РµРј РґР°С‚Р°СЃРµС‚ РёР· {data_path}")
    df = pd.read_parquet(data_path)
    print(f"рџ“¦ Р—Р°РіСЂСѓР¶РµРЅРѕ {len(df)} СЃС‚СЂРѕРє, РєРѕР»РѕРЅРєРё: {list(df.columns)}")

    # РџСЂРѕРІРµСЂРєР° Рё С„РёР»СЊС‚СЂР°С†РёСЏ
    required_cols = {"code", "docstring"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"вќЊ Р’ РґР°С‚Р°СЃРµС‚Рµ РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ РєРѕР»РѕРЅРєРё {required_cols}, РЅР°Р№РґРµРЅРѕ: {set(df.columns)}"
        )

    # РћСЃС‚Р°РІР»СЏРµРј С‚РѕР»СЊРєРѕ РЅСѓР¶РЅС‹Рµ РєРѕР»РѕРЅРєРё
    df = df[list(required_cols)]

    # РЈРґР°Р»СЏРµРј РїСѓСЃС‚С‹Рµ Р·РЅР°С‡РµРЅРёСЏ Рё СЃС‚СЂРѕРєРё
    df = df.dropna(subset=["code", "docstring"])
    df = df[df["code"].str.strip() != ""]
    df = df[df["docstring"].str.strip() != ""]

    print(f"вњ… РџРѕСЃР»Рµ С„РёР»СЊС‚СЂР°С†РёРё РѕСЃС‚Р°Р»РѕСЃСЊ {len(df)} РїСЂРёРјРµСЂРѕРІ")

    return Dataset.from_pandas(df)


# === 2. РўРѕРєРµРЅРёР·Р°С†РёСЏ ===
def preprocess_function(examples, tokenizer):
    inputs = [
        "РЎРѕР·РґР°Р№ docstring РґР»СЏ СЃР»РµРґСѓСЋС‰РµР№ С„СѓРЅРєС†РёРё Python:\n" + code
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


# === 3. Р¤СѓРЅРєС†РёСЏ РґР»СЏ РѕР±СѓС‡РµРЅРёСЏ ===
def train_model(data_path: str):
    ds = load_local_dataset(data_path)

    torch.set_num_threads(32)

    # Р Р°Р·РґРµР»РµРЅРёРµ РЅР° train/test
    split_ds = ds.train_test_split(test_size=0.1, seed=42)
    dataset = DatasetDict({
        "train": split_ds["train"],
        "test": split_ds["test"]
    })

    print("рџ”№ Р—Р°РіСЂСѓР¶Р°РµРј Р»РѕРєР°Р»СЊРЅС‹Р№ С‚РѕРєРµРЅРёР·Р°С‚РѕСЂ Рё РјРѕРґРµР»СЊ РёР· local-codet5-small...")

    model_path = "local-codet5-small"

    # Р—Р°РіСЂСѓР¶Р°РµРј С‚РѕРєРµРЅРёР·Р°С‚РѕСЂ Рё РјРѕРґРµР»СЊ Р»РѕРєР°Р»СЊРЅРѕ
    tokenizer = RobertaTokenizer.from_pretrained(model_path)
    config = T5Config.from_pretrained(model_path)
    model = T5ForConditionalGeneration.from_pretrained(model_path, config=config)

    print("вњ… РњРѕРґРµР»СЊ Рё С‚РѕРєРµРЅРёР·Р°С‚РѕСЂ СѓСЃРїРµС€РЅРѕ Р·Р°РіСЂСѓР¶РµРЅС‹ Р»РѕРєР°Р»СЊРЅРѕ.")
    # РџСЂРѕРІРµСЂСЏРµРј GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"рџ’» РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ СѓСЃС‚СЂРѕР№СЃС‚РІРѕ: {device}")
    if device == "cuda":
        gpu = torch.cuda.get_device_properties(0)
        total_gb = gpu.total_memory / 1024**3
        print(f"вњ… GPU: {gpu.name} | CUDA: {torch.version.cuda} | VRAM: {total_gb:.1f} GB")
    else:
        print("вљ пёЏ CUDA РЅРµРґРѕСЃС‚СѓРїРЅР°. РџСЂРѕРІРµСЂСЊС‚Рµ, С‡С‚Рѕ СѓСЃС‚Р°РЅРѕРІР»РµРЅ torch СЃ CUDA, РЅР°РїСЂРёРјРµСЂ torch==2.9.0+cu126.")
    model.to(device)

    # РўРѕРєРµРЅРёР·Р°С†РёСЏ
    print("рџ”„ РўРѕРєРµРЅРёР·Р°С†РёСЏ РґР°С‚Р°СЃРµС‚Р°...")
    tokenized_ds = dataset.map(
        lambda x: preprocess_function(x, tokenizer),
        batched=True,
        remove_columns=dataset["train"].column_names,
    )


    # Р—Р°РіСЂСѓР¶Р°РµРј РјРµС‚СЂРёРєРё
    bleu = evaluate.load("bleu")
    rouge = evaluate.load("rouge")

    def compute_metrics(eval_preds):
        preds, labels = eval_preds

        # Р Р°СЃРєРѕРґРёСЂСѓРµРј С‚РѕРєРµРЅС‹ РІ С‚РµРєСЃС‚
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)

        # РЈР±РёСЂР°РµРј РїСЂРѕР±РµР»С‹ Рё РїСѓСЃС‚С‹Рµ СЃС‚СЂРѕРєРё
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



    # РџР°СЂР°РјРµС‚СЂС‹ РѕР±СѓС‡РµРЅРёСЏ
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

    # РћР±СѓС‡РµРЅРёРµ
    print("рџљЂ РќР°С‡Р°Р»Рѕ РѕР±СѓС‡РµРЅРёСЏ...")
    trainer.train()

    # РЎРѕС…СЂР°РЅРµРЅРёРµ
    save_dir = "./git_model"
    trainer.save_model(save_dir)
    tokenizer.save_pretrained(save_dir)
    print(f"вњ… РњРѕРґРµР»СЊ СЃРѕС…СЂР°РЅРµРЅР° РІ {save_dir}")

    return tokenizer, model


# === 4. Р¤СѓРЅРєС†РёСЏ С‚РµСЃС‚РёСЂРѕРІР°РЅРёСЏ РјРѕРґРµР»Рё ===
def test_model(tokenizer, model):
    print("\nрџ”Ћ РўРµСЃС‚РёСЂРѕРІР°РЅРёРµ РјРѕРґРµР»Рё: РІРІРµРґРёС‚Рµ Python-РєРѕРґ РґР»СЏ РіРµРЅРµСЂР°С†РёРё docstring.")
    print("Р’РІРµРґРёС‚Рµ 'exit' РґР»СЏ РІС‹С…РѕРґР°.\n")

    while True:
        code_snippet = input("рџ’¬ Р’РІРµРґРёС‚Рµ РєРѕРґ: ")
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
        print(f"рџ“ РЎРіРµРЅРµСЂРёСЂРѕРІР°РЅРЅС‹Р№ docstring:\n{docstring}\n")


# === 5. Р—Р°РїСѓСЃРє ===
if __name__ == "__main__":
    DATA_PATH = "git_dataset.parquet"

    tokenizer, model = train_model(DATA_PATH)
    test_model(tokenizer, model)
