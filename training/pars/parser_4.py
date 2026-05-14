#!/usr/bin/env python3
"""
collect_github_dataset_v3.py
---------------------------------
Асинхронный сбор Python-репозиториев с GitHub.
Извлечение функций с Google-style docstrings.
Поддержка:
- Ротация токенов
- Пагинация + разные диапазоны stars
- Пропуск уже собранных репозиториев
- Промежуточные сохранения
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
from tqdm import tqdm

DetectorFactory.seed = 0  # стабильность langdetect

# ========== НАСТРОЙКИ ==========

TOKENS = [
    token.strip()
    for token in os.getenv("GITHUB_TOKENS", os.getenv("GITHUB_TOKEN", "")).split(",")
    if token.strip()
]

if not TOKENS:
    raise RuntimeError("Set GITHUB_TOKEN or comma-separated GITHUB_TOKENS before running this script.")

OUTPUT_FILE = "functions_with_docstrings_4.parquet"
CHECKPOINT_DIR = "checkpoints"
REPOS_TARGET = 1000          # сколько репозиториев обработать
PER_PAGE = 100               # максимум 100
PAGES = 10                   # максимум 10 (1000 репозиториев)
MAX_FILES_PER_REPO = 100     # максимум .py файлов
MAX_CODE_TOKENS = 300        # лимит слов в коде
MAX_WORKERS = 12             # потоки для клонирования
SAVE_EVERY = 100             # сохранять каждые N репозиториев
SLEEP_BETWEEN_PAGES = 1.2    # пауза между запросами
LANGUAGE = "python"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def rotate_token(index: int) -> str:
    return TOKENS[index % len(TOKENS)]

def is_google_style_docstring(docstring: str) -> bool:
    return bool(docstring and "Args:" in docstring and "Returns:" in docstring)

def safe_detect_lang(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

# ========== ИЗВЛЕЧЕНИЕ ФУНКЦИЙ ИЗ ФАЙЛА ==========

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
            if not doc or not is_google_style_docstring(doc):
                continue

            lang = safe_detect_lang(doc)
            if lang != "en":
                continue

            try:
                code = ast.get_source_segment(src, node)
            except Exception:
                continue

            if len(code.split()) > MAX_CODE_TOKENS:
                continue

            entries.append({
                "function_name": node.name,
                "code": code.strip(),
                "docstring": doc.strip().replace("\r", "").replace("\n\n", "\n")
            })
    return entries

# ========== КЛОНИРОВАНИЕ И ПАРСИНГ РЕПОЗИТОРИЯ ==========

def process_repository_clone(repo_url):
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
                        for e in entries:
                            e["repo_url"] = repo_url
                            e["file_path"] = path.replace(tmpdir + os.sep, "")
                        results.extend(entries)
                    except Exception:
                        continue

                    file_count += 1
                    if file_count >= MAX_FILES_PER_REPO:
                        break
            if file_count >= MAX_FILES_PER_REPO:
                break
    return results

# ========== СБОР URL РЕПОЗИТОРИЕВ (с диапазонами stars) ==========

def generate_star_queries():
    """Разные диапазоны популярности, чтобы обойти лимит 1000 результатов."""
    return [
        "stars:>5000",
        "stars:1000..5000",
        "stars:500..1000",
        "stars:200..500",
        "stars:100..200",
        "stars:50..100",
        "stars:20..50",
        "stars:10..20",
        "stars:5..10",
        "stars:1..5",
    ]

async def fetch_repos_for_query(session, query, page, token):
    headers = {"Authorization": f"token {token}"}
    full_q = f"language:{LANGUAGE}+{query}"
    url = f"https://api.github.com/search/repositories?q={full_q}&sort=stars&order=desc&per_page={PER_PAGE}&page={page}"

    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            text = await resp.text()
            print(f"⚠️ Ошибка {resp.status} для {query}, стр. {page}: {text[:100]}")
            if resp.status == 403:
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset:
                    sleep_for = max(10, int(reset) - int(time.time()) + 5)
                    print(f"⏳ Превышен лимит. Ждём {sleep_for} сек...")
                    await asyncio.sleep(sleep_for)
                    return []
            return []
        data = await resp.json()
        return [item["clone_url"] for item in data.get("items", [])]

async def gather_repo_urls_with_queries(processed_set, target_count=REPOS_TARGET):
    queries = generate_star_queries()
    found = []
    async with aiohttp.ClientSession() as session:
        token_index = 0
        for q in queries:
            for page in range(1, PAGES + 1):
                token = rotate_token(token_index)
                token_index += 1
                urls = await fetch_repos_for_query(session, q, page, token)
                if not urls:
                    break
                for u in urls:
                    if len(found) >= target_count:
                        return found
                    if u in processed_set or u in found:
                        continue
                    found.append(u)
                await asyncio.sleep(SLEEP_BETWEEN_PAGES)
            await asyncio.sleep(0.5)
    return found[:target_count]

# ========== ОСНОВНОЙ WORKFLOW ==========

async def main():
    print("🔹 Начинаем сбор списка репозиториев...")

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
    print(f"📦 Уже собрано {len(processed_set)} репозиториев (будут пропущены).")

    repo_urls = await gather_repo_urls_with_queries(processed_set, REPOS_TARGET)
    print(f"✅ Найдено {len(repo_urls)} новых репозиториев для обработки.")

    accumulated = []
    partial_parquet = os.path.join(CHECKPOINT_DIR, "partial_results.parquet")
    if os.path.exists(partial_parquet):
        try:
            df_existing = pd.read_parquet(partial_parquet)
            accumulated = df_existing.to_dict(orient="records")
            print(f"📂 Загружено {len(accumulated)} записей из checkpoint.")
        except Exception:
            print("⚠️ Ошибка загрузки checkpoint, начинаем заново.")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [(repo_url, executor.submit(process_repository_clone, repo_url)) for repo_url in repo_urls]

        processed_counter = 0
        for repo_url, fut in tqdm(futures, desc="🔍 Обработка репозиториев"):
            try:
                result = fut.result()
            except Exception:
                result = []
            if result:
                accumulated.extend(result)

            with open(processed_repos_file, "a", encoding="utf-8") as pf:
                pf.write(json.dumps({"repo_url": repo_url, "timestamp": int(time.time())}) + "\n")

            processed_counter += 1
            if processed_counter % SAVE_EVERY == 0:
                df = pd.DataFrame(accumulated)
                if not df.empty:
                    df = df.drop_duplicates(subset=["code"])
                    df.to_parquet(partial_parquet, index=False)
                    print(f"💾 Checkpoint: сохранено {len(df)} записей.")

    df_final = pd.DataFrame(accumulated)
    if not df_final.empty:
        df_final = df_final.drop_duplicates(subset=["code"])
        df_final.to_parquet(OUTPUT_FILE, index=False)
        print(f"✅ Готово. Сохранено {len(df_final)} записей в {OUTPUT_FILE}")
    else:
        print("⚠️ Не найдено функций. Проверь фильтры или токены.")

if __name__ == "__main__":
    asyncio.run(main())
