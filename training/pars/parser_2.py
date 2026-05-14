#!/usr/bin/env python3
"""
collect_github_dataset.py

Собирает репозитории с GitHub, извлекает функции с Google-style docstrings (Args:, Returns:)
и сохраняет пары {code, docstring, function_name, repo_url, file_path} в parquet.

Особенности:
- Асинхронный сбор списка репозиториев с пагинацией и разбиением по created: диапазонам.
- Ротация нескольких GitHub токенов.
- Многопоточное клонирование и парсинг репозиториев.
- Проверка языка docstring (английский).
- Ограничение длины функции.
- Промежуточное сохранение (checkpoint) каждые SAVE_EVERY репозиториев.
"""

import os
import re
import ast
import json
import time
import tempfile
import asyncio
import aiohttp
import pandas as pd
from git import Repo
from langdetect import detect, DetectorFactory
from concurrent.futures import ThreadPoolExecutor
from tqdm.asyncio import tqdm as atqdm
from tqdm import tqdm

DetectorFactory.seed = 0  # для стабильности langdetect

# ========== НАСТРОЙКИ ==========
TOKENS = [
    token.strip()
    for token in os.getenv("GITHUB_TOKENS", os.getenv("GITHUB_TOKEN", "")).split(",")
    if token.strip()
]

if not TOKENS:
    raise RuntimeError("Set GITHUB_TOKEN or comma-separated GITHUB_TOKENS before running this script.")

OUTPUT_FILE = "functions_with_docstrings.parquet"
CHECKPOINT_DIR = "checkpoints"
REPOS_TARGET = 10000         # сколько репозиториев хотим обработать
PER_PAGE = 100              # GitHub API max per_page
PAGES_PER_QUERY = 10        # обычно до 10 страниц (1000) — но мы разбиваем по датам
MAX_FILES_PER_REPO = 100
MAX_CODE_TOKENS = 500       # лимит слов в коде функции
MAX_WORKERS = 16            # потоки для клонирования/парсинга
SAVE_EVERY = 1000             # сохранять промежуточно каждые N репозиториев
GITHUB_SEARCH_SLEEP = 1.2   # пауза между запросами поиска (сек)

# Разбиваем по диапазонам дат (created:) - список кортежей (start, end)
# Подберите периоды так, чтобы в каждом диапазоне было <=1000 результатов.
# Пример: по годам (набираем столько диапазонов, сколько нужно)
DATE_RANGES = [
    ("2010-01-01", "2012-12-31"),
    ("2013-01-01", "2014-12-31"),
    ("2015-01-01", "2016-12-31"),
    ("2017-01-01", "2018-12-31"),
    ("2019-01-01", "2019-12-31"),
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31"),
    ("2023-01-01", "2023-12-31"),
    ("2024-01-01", "2024-12-31"),
]
# Корректируйте DATE_RANGES, пока не накопите REPOS_TARGET репо.

# =================================

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# ========== Утилиты ==========
def rotate_token(index: int) -> str:
    return TOKENS[index % len(TOKENS)]

def is_google_style_docstring(docstring: str) -> bool:
    if not docstring:
        return False
    return "Args:" in docstring and "Returns:" in docstring

def safe_detect_lang(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

# ========== Парсер функций ==========
def extract_functions_from_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        return []

    entries = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if not doc:
                continue
            if not is_google_style_docstring(doc):
                continue
            # language check
            lang = safe_detect_lang(doc)
            if lang != "en":
                continue
            # source segment
            try:
                code = ast.get_source_segment(src, node)
            except Exception:
                code = None
            if not code:
                continue
            # length filter
            if len(code.split()) > MAX_CODE_TOKENS:
                continue

            entries.append({
                "function_name": node.name,
                "code": code.strip(),
                "docstring": doc.strip().replace("\r", "").replace("\n\n", "\n")
            })
    return entries

# ========== Клонирование и парсинг репо ==========
def process_repository_clone(repo_url, max_files=MAX_FILES_PER_REPO):
    """Клонирует репо (шallow depth=1) и парсит .py файлы. Возвращает список записей."""
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            Repo.clone_from(repo_url, tmpdir, depth=1)
        except Exception:
            return results

        file_count = 0
        for root, _, files in os.walk(tmpdir):
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    try:
                        entries = extract_functions_from_file(path)
                        # добавим контекст репо/file для каждого
                        for e in entries:
                            e["repo_url"] = repo_url
                            e["file_path"] = path.replace(tmpdir + os.sep, "")
                        results.extend(entries)
                    except Exception:
                        continue

                    file_count += 1
                    if file_count >= max_files:
                        break
            if file_count >= max_files:
                break
    return results

# ========== Асинхронный сбор списка репозиториев (с пагинацией и датами) ==========
async def fetch_repos_for_range(session, start_date, end_date, token, per_page=PER_PAGE, pages=PAGES_PER_QUERY):
    """Запрос search/repositories для диапазона created: start..end. Возвращает список clone_url."""
    urls = []
    headers = {"Authorization": f"token {token}"}
    base_q = f"language:python+created:{start_date}..{end_date}+stars:>1"
    for page in range(1, pages + 1):
        url = (
            f"https://api.github.com/search/repositories"
            f"?q={base_q}&sort=stars&order=desc&per_page={per_page}&page={page}"
        )
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Warning: GitHub search returned status {resp.status} (page {page}): {text[:200]}")
                # если rate limit, попытка ожидать
                if resp.status == 403:
                    reset = resp.headers.get("X-RateLimit-Reset")
                    if reset:
                        sleep_for = max(10, int(reset) - int(time.time()) + 5)
                        print(f"Rate limit hit. Sleeping for {sleep_for}s")
                        await asyncio.sleep(sleep_for)
                        continue
                await asyncio.sleep(GITHUB_SEARCH_SLEEP)
                continue

            data = await resp.json()
            items = data.get("items", [])
            if not items:
                break
            urls.extend([it["clone_url"] for it in items])
            await asyncio.sleep(GITHUB_SEARCH_SLEEP)
    return urls

async def gather_repo_urls(target_count=REPOS_TARGET):
    repo_urls = []
    async with aiohttp.ClientSession() as session:
        token_index = 0
        # обходим диапазоны дат
        for (start, end) in DATE_RANGES:
            # rotate token
            token = rotate_token(token_index)
            token_index += 1
            urls = await fetch_repos_for_range(session, start, end, token)
            for u in urls:
                if len(repo_urls) >= target_count:
                    return repo_urls
                if u not in repo_urls:
                    repo_urls.append(u)
            # небольшая пауза между диапазонами
            await asyncio.sleep(0.5)
            # защита от слишком быстрой работы
            if len(repo_urls) >= target_count:
                break
    return repo_urls

# ========== Основной workflow ==========
async def main():
    print("=== Start collecting repo URLs ===")
    repo_urls = await gather_repo_urls(REPOS_TARGET)
    print(f"Found {len(repo_urls)} repo URLs; preparing to clone and parse.")

    # checkpoint: если уже есть файл с обработанными репо — загрузим, чтобы не дублировать
    processed_repos_file = os.path.join(CHECKPOINT_DIR, "processed_repos.jsonl")
    processed_set = set()
    if os.path.exists(processed_repos_file):
        with open(processed_repos_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    processed_set.add(rec.get("repo_url"))
                except Exception:
                    continue

    # prepare output list and possibly load already saved partial parquet
    accumulated = []
    partial_parquet = os.path.join(CHECKPOINT_DIR, "partial_results.parquet")
    if os.path.exists(partial_parquet):
        try:
            df_existing = pd.read_parquet(partial_parquet)
            accumulated = df_existing.to_dict(orient="records")
            print(f"Loaded {len(accumulated)} previously saved records from checkpoint.")
        except Exception:
            print("Cannot load partial parquet checkpoint; will start fresh.")

    # prepare thread pool for cloning/parsing
    total = len(repo_urls)
    to_process = [u for u in repo_urls if u not in processed_set]
    print(f"{len(to_process)} repos to process (skipping {len(repo_urls)-len(to_process)} already processed).")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i, repo_url in enumerate(to_process, 1):
            futures.append((i, repo_url, executor.submit(process_repository_clone, repo_url, MAX_FILES_PER_REPO)))

        # iterate and collect results; save periodically
        processed_counter = 0
        for idx, repo_url, fut in tqdm(futures, desc="Cloning & parsing repos", total=len(futures)):
            try:
                result = fut.result()
            except Exception:
                result = []
            # append results
            if result:
                accumulated.extend(result)

            # mark processed repo in checkpoint file
            with open(processed_repos_file, "a", encoding="utf-8") as pf:
                pf.write(json.dumps({"repo_url": repo_url, "timestamp": int(time.time())}) + "\n")

            processed_counter += 1

            # Save intermediate every SAVE_EVERY repos
            if processed_counter % SAVE_EVERY == 0:
                df = pd.DataFrame(accumulated)
                if not df.empty:
                    # dedupe by code
                    df = df.drop_duplicates(subset=["code"])
                    df.to_parquet(partial_parquet, index=False)
                    print(f"Checkpoint: saved {len(df)} records to {partial_parquet}")

    # final save
    df_final = pd.DataFrame(accumulated)
    if not df_final.empty:
        df_final = df_final.drop_duplicates(subset=["code"])
        df_final.to_parquet(OUTPUT_FILE, index=False)
        print(f"Done. Saved final dataset to {OUTPUT_FILE}. Total records: {len(df_final)}")
    else:
        print("No functions extracted. Check logs and access rights.")

if __name__ == "__main__":
    asyncio.run(main())
