from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


CODE_COLUMN_CANDIDATES = (
    "code",
    "source",
    "source_code",
    "original_string",
    "func_code",
    "function_code",
)

DOC_COLUMN_CANDIDATES = (
    "docstring",
    "doc",
    "documentation",
    "summary",
    "comment",
    "description",
)

REPO_COLUMN_CANDIDATES = (
    "repo_url",
    "repo",
    "repository",
    "project",
    "repo_name",
)

FILE_COLUMN_CANDIDATES = (
    "file_path",
    "path",
    "filepath",
    "file",
)

FUNCTION_COLUMN_CANDIDATES = (
    "function_name",
    "func_name",
    "name",
)


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.is_dir():
        try:
            from datasets import Dataset, DatasetDict, load_from_disk
        except ImportError as exc:
            raise ValueError(
                f"{path} looks like a dataset directory, but datasets is unavailable"
            ) from exc

        loaded = load_from_disk(str(path))
        if isinstance(loaded, DatasetDict):
            frames = []
            for split_name, split in loaded.items():
                frame = split.to_pandas()
                frame["dataset_split"] = split_name
                frames.append(frame)
            return pd.concat(frames, ignore_index=True)
        if isinstance(loaded, Dataset):
            return loaded.to_pandas()
        raise ValueError(f"Unsupported dataset directory content: {path}")

    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        try:
            return pd.read_csv(path)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="cp1251")
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    if suffix == ".json":
        return pd.read_json(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported dataset format: {path}")


def find_column(
    columns: Iterable[str],
    explicit: Optional[str],
    candidates: Iterable[str],
) -> Optional[str]:
    column_set = {str(col).lower(): str(col) for col in columns}
    if explicit:
        key = explicit.lower()
        if key in column_set:
            return column_set[key]
        raise ValueError(f"Column '{explicit}' was requested but not found")
    for candidate in candidates:
        key = candidate.lower()
        if key in column_set:
            return column_set[key]
    return None


def normalize_code(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if not isinstance(value, str):
        if isinstance(value, (list, tuple)):
            value = " ".join(str(item) for item in value)
        else:
            value = str(value)
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def normalize_docstring(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if not isinstance(value, str):
        if isinstance(value, (list, tuple)):
            value = " ".join(str(item) for item in value)
        else:
            value = str(value)
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class _DocstringStripper(ast.NodeTransformer):
    def _strip_body_docstring(self, node):
        body = getattr(node, "body", None)
        if not body:
            return node
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            node.body = body[1:] or [ast.Pass()]
        return node

    def visit_Module(self, node):
        self.generic_visit(node)
        return self._strip_body_docstring(node)

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        return self._strip_body_docstring(node)

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        return self._strip_body_docstring(node)

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        return self._strip_body_docstring(node)


def strip_source_docstrings(code: str) -> str:
    if not code:
        return ""
    try:
        tree = ast.parse(code)
        tree = _DocstringStripper().visit(tree)
        ast.fix_missing_locations(tree)
        return ast.unparse(tree).strip()
    except Exception:
        return code.strip()


def canonical_code(code: str) -> str:
    cleaned = strip_source_docstrings(code)
    try:
        tree = ast.parse(cleaned)
        return ast.dump(tree, include_attributes=False)
    except Exception:
        return re.sub(r"\s+", " ", cleaned).strip()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def quality_flags(
    code: str,
    docstring: str,
    min_code_chars: int,
    min_doc_chars: int,
    max_code_chars: int,
    max_doc_chars: int,
    require_def: bool,
    require_google_style: bool,
) -> list[str]:
    flags: list[str] = []
    if len(code) < min_code_chars:
        flags.append("code_too_short")
    if len(docstring) < min_doc_chars:
        flags.append("docstring_too_short")
    if len(code) > max_code_chars:
        flags.append("code_too_long")
    if len(docstring) > max_doc_chars:
        flags.append("docstring_too_long")
    if code and docstring and code.strip() == docstring.strip():
        flags.append("code_equals_docstring")
    if require_def and not re.search(r"\b(async\s+def|def|class)\s+\w+", code):
        flags.append("missing_python_def_or_class")
    if require_google_style and not ("Args:" in docstring and "Returns:" in docstring):
        flags.append("not_google_style")
    return flags


def project_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent.joinpath(*parts)


def write_json(path: str | Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
