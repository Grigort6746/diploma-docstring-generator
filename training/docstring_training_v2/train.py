from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from datasets import Dataset, DatasetDict
from nltk.translate.bleu_score import SmoothingFunction, corpus_bleu
from rouge_score import rouge_scorer
from transformers import (
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    EarlyStoppingCallback,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    T5ForConditionalGeneration,
)


DEFAULT_PROMPT = "Generate a Python docstring:\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune CodeT5 for docstring generation.")
    parser.add_argument("--data-dir", default="docstring_training_v2/data/max_merged")
    parser.add_argument("--train-file", default=None)
    parser.add_argument("--validation-file", default=None)
    parser.add_argument("--test-file", default=None)
    parser.add_argument("--model-path", default="local-codet5-small")
    parser.add_argument("--output-dir", default="docstring_training_v2/runs/codet5_docstrings")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-source-length", type=int, default=512)
    parser.add_argument("--max-target-length", type=int, default=160)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--eval-batch-size", type=int, default=4)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=2)
    parser.add_argument("--epochs", type=float, default=4.0)
    parser.add_argument("--learning-rate", type=float, default=3e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup-steps", type=int, default=0)
    parser.add_argument("--warmup-ratio", type=float, default=0.03)
    parser.add_argument("--label-smoothing", type=float, default=0.05)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--save-total-limit", type=int, default=3)
    parser.add_argument("--early-stopping-patience", type=int, default=2)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--logging-steps", type=int, default=100)
    parser.add_argument("--eval-accumulation-steps", type=int, default=16)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--no-group-by-length", action="store_true")
    parser.add_argument("--no-evaluate-test", action="store_true")
    parser.add_argument("--no-checkpoints", action="store_true")
    parser.add_argument("--skip-final-save", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_data_files(args: argparse.Namespace) -> dict[str, Path]:
    data_dir = Path(args.data_dir)
    return {
        "train": Path(args.train_file) if args.train_file else data_dir / "train.parquet",
        "validation": Path(args.validation_file)
        if args.validation_file
        else data_dir / "validation.parquet",
        "test": Path(args.test_file) if args.test_file else data_dir / "test.parquet",
    }


def read_split(path: Path) -> Dataset:
    if not path.exists():
        raise FileNotFoundError(f"Dataset split not found: {path}")
    df = pd.read_parquet(path)
    required = {"code", "docstring"}
    if not required.issubset(df.columns):
        raise ValueError(f"{path} must contain columns: {required}")
    df = df[["code", "docstring"]].dropna()
    df = df[(df["code"].str.strip() != "") & (df["docstring"].str.strip() != "")]
    return Dataset.from_pandas(df.reset_index(drop=True), preserve_index=False)


def build_dataset(args: argparse.Namespace) -> DatasetDict:
    files = resolve_data_files(args)
    dataset = DatasetDict(
        {
            "train": read_split(files["train"]),
            "validation": read_split(files["validation"]),
        }
    )
    if files["test"].exists():
        dataset["test"] = read_split(files["test"])
    return dataset


def print_device() -> None:
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        total_gb = props.total_memory / 1024**3
        print(f"Device: cuda")
        print(f"GPU: {props.name}")
        print(f"CUDA build: {torch.version.cuda}")
        print(f"VRAM: {total_gb:.1f} GB")
    else:
        print("Device: cpu")
        print("CUDA is not available. Check that torch is installed with CUDA support.")


def plot_training_curves(log_history: list[dict], output_dir: Path) -> None:
    if not log_history:
        return

    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    history = pd.DataFrame(log_history)
    history.to_csv(output_dir / "training_log.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def plot_series(
        filename: str,
        title: str,
        ylabel: str,
        series: list[tuple[str, str]],
    ) -> None:
        plt.figure(figsize=(11, 6))
        plotted = False
        for column, label in series:
            if column not in history.columns:
                continue
            subset = history[history[column].notna() & history["step"].notna()]
            if subset.empty:
                continue
            plt.plot(subset["step"], subset[column], marker="o", linewidth=1.5, label=label)
            plotted = True
        if not plotted:
            plt.close()
            return
        plt.title(title)
        plt.xlabel("Training step")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(plots_dir / filename, dpi=160)
        plt.close()

    plot_series(
        "loss_curves.png",
        "Training and Validation Loss",
        "Loss",
        [("loss", "train loss"), ("eval_loss", "validation loss")],
    )
    plot_series(
        "quality_metrics.png",
        "Generated Docstring Quality Metrics",
        "Score",
        [
            ("eval_rougeL", "ROUGE-L"),
            ("eval_rouge1", "ROUGE-1"),
            ("eval_bleu", "BLEU"),
        ],
    )
    plot_series(
        "learning_rate.png",
        "Learning Rate Schedule",
        "Learning rate",
        [("learning_rate", "learning rate")],
    )

    final_metrics = {}
    metric_columns = [
        "eval_loss",
        "eval_bleu",
        "eval_rouge1",
        "eval_rougeL",
        "validation_loss",
        "validation_bleu",
        "validation_rouge1",
        "validation_rougeL",
        "test_loss",
        "test_bleu",
        "test_rouge1",
        "test_rougeL",
    ]
    for column in metric_columns:
        if column in history.columns:
            values = history[column].dropna()
            if not values.empty:
                final_metrics[column] = float(values.iloc[-1])
    (output_dir / "final_metric_snapshot.json").write_text(
        json.dumps(final_metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print_device()
    dataset = build_dataset(args)
    print(dataset)

    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    model = T5ForConditionalGeneration.from_pretrained(args.model_path)
    if args.gradient_checkpointing:
        model.config.use_cache = False

    def preprocess(batch):
        inputs = [args.prompt + code for code in batch["code"]]
        model_inputs = tokenizer(
            inputs,
            max_length=args.max_source_length,
            truncation=True,
        )
        labels = tokenizer(
            batch["docstring"],
            max_length=args.max_target_length,
            truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized = dataset.map(
        preprocess,
        batched=True,
        remove_columns=dataset["train"].column_names,
        desc="Tokenizing",
    )

    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        label_pad_token_id=-100,
        pad_to_multiple_of=8 if args.fp16 else None,
    )

    rouge = rouge_scorer.RougeScorer(["rouge1", "rougeL"], use_stemmer=True)
    bleu_smoothing = SmoothingFunction().method4

    def compute_metrics(eval_preds):
        preds, labels = eval_preds
        if isinstance(preds, tuple):
            preds = preds[0]
        labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
        decoded_preds = tokenizer.batch_decode(preds, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        decoded_preds = [pred.strip() for pred in decoded_preds]
        decoded_labels = [label.strip() for label in decoded_labels]

        references = [[label.split()] for label in decoded_labels]
        predictions = [pred.split() for pred in decoded_preds]
        if any(predictions) and any(refs[0] for refs in references):
            bleu_score = corpus_bleu(
                references,
                predictions,
                smoothing_function=bleu_smoothing,
            )
        else:
            bleu_score = 0.0

        rouge_scores = [
            rouge.score(label, pred) for pred, label in zip(decoded_preds, decoded_labels)
        ]
        if rouge_scores:
            rouge1 = float(np.mean([score["rouge1"].fmeasure for score in rouge_scores]))
            rouge_l = float(np.mean([score["rougeL"].fmeasure for score in rouge_scores]))
        else:
            rouge1 = 0.0
            rouge_l = 0.0

        metrics = {
            "bleu": bleu_score * 100,
            "rouge1": rouge1 * 100,
            "rougeL": rouge_l * 100,
        }
        return {key: round(value, 4) for key, value in metrics.items()}

    save_strategy = "no" if args.no_checkpoints else "epoch"
    load_best_model = not args.no_checkpoints

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        evaluation_strategy="epoch",
        save_strategy=save_strategy,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        num_train_epochs=args.epochs,
        weight_decay=args.weight_decay,
        warmup_steps=args.warmup_steps,
        warmup_ratio=args.warmup_ratio,
        label_smoothing_factor=args.label_smoothing,
        max_grad_norm=args.max_grad_norm,
        predict_with_generate=True,
        generation_max_length=args.max_target_length,
        generation_num_beams=args.num_beams,
        logging_dir=str(output_dir / "logs"),
        logging_steps=args.logging_steps,
        save_total_limit=args.save_total_limit,
        load_best_model_at_end=load_best_model,
        metric_for_best_model="eval_rougeL",
        greater_is_better=True,
        fp16=args.fp16,
        gradient_checkpointing=args.gradient_checkpointing,
        group_by_length=not args.no_group_by_length,
        eval_accumulation_steps=args.eval_accumulation_steps,
        optim="adamw_torch",
        dataloader_num_workers=0,
        report_to="none",
        seed=args.seed,
    )

    callbacks = []
    if args.early_stopping_patience > 0 and not args.no_checkpoints:
        callbacks.append(
            EarlyStoppingCallback(
                early_stopping_patience=args.early_stopping_patience,
            )
        )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=callbacks,
    )

    run_config = vars(args).copy()
    run_config["torch"] = torch.__version__
    run_config["torch_cuda_build"] = torch.version.cuda
    run_config["cuda_available"] = torch.cuda.is_available()
    run_config["effective_train_batch_size"] = (
        args.batch_size * args.gradient_accumulation_steps
    )
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    trainer.train()

    if not args.skip_final_save:
        final_dir = output_dir / "final"
        trainer.save_model(str(final_dir))
        tokenizer.save_pretrained(str(final_dir))
        print(f"Saved final model to {final_dir}")

    metrics = trainer.evaluate(tokenized["validation"], metric_key_prefix="validation")
    if "test" in tokenized and not args.no_evaluate_test:
        metrics.update(trainer.evaluate(tokenized["test"], metric_key_prefix="test"))
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    (output_dir / "trainer_state_log.json").write_text(
        json.dumps(trainer.state.log_history, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    if not args.no_plots:
        plot_training_curves(trainer.state.log_history, output_dir)
    print(metrics)


if __name__ == "__main__":
    main()
