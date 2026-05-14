from __future__ import annotations

import argparse
from pathlib import Path

import torch
from transformers import AutoTokenizer, T5ForConditionalGeneration


DEFAULT_PROMPT = "Generate a Python docstring:\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a docstring with a trained model.")
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--code-file", default=None)
    parser.add_argument("--code", default=None)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--max-source-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=128)
    parser.add_argument("--num-beams", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=1.0)
    return parser.parse_args()


def read_code(args: argparse.Namespace) -> str:
    if args.code_file:
        return Path(args.code_file).read_text(encoding="utf-8")
    if args.code:
        return args.code
    raise ValueError("Pass --code-file or --code")


def main() -> None:
    args = parse_args()
    code = read_code(args).strip()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = T5ForConditionalGeneration.from_pretrained(args.model_dir).to(device)
    model.eval()

    encoded = tokenizer(
        args.prompt + code,
        max_length=args.max_source_length,
        truncation=True,
        return_tensors="pt",
    )
    encoded = {key: value.to(device) for key, value in encoded.items()}

    with torch.no_grad():
        output_ids = model.generate(
            **encoded,
            max_new_tokens=args.max_new_tokens,
            num_beams=args.num_beams,
            early_stopping=True,
            no_repeat_ngram_size=3,
            temperature=args.temperature,
        )

    print(tokenizer.decode(output_ids[0], skip_special_tokens=True).strip())


if __name__ == "__main__":
    main()
