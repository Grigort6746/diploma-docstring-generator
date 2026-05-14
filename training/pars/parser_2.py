#!/usr/bin/env python3
"""
collect_github_dataset.py

РЎРѕР±РёСЂР°РµС‚ СЂРµРїРѕР·РёС‚РѕСЂРёРё СЃ GitHub, РёР·РІР»РµРєР°РµС‚ С„СѓРЅРєС†РёРё СЃ Google-style docstrings (Args:, Returns:)
Рё СЃРѕС…СЂР°РЅСЏРµС‚ РїР°СЂС‹ {code, docstring, function_name, repo_url, file_path} РІ parquet.

РћСЃРѕР±РµРЅРЅРѕСЃС‚Рё:
- РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ СЃР±РѕСЂ СЃРїРёСЃРєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ СЃ РїР°РіРёРЅР°С†РёРµР№ Рё СЂР°Р·Р±РёРµРЅРёРµРј РїРѕ created: РґРёР°РїР°Р·РѕРЅР°Рј.
- Р РѕС‚Р°С†РёСЏ РЅРµСЃРєРѕР»СЊРєРёС… GitHub С‚РѕРєРµРЅРѕРІ.
- РњРЅРѕРіРѕРїРѕС‚РѕС‡РЅРѕРµ РєР»РѕРЅРёСЂРѕРІР°РЅРёРµ Рё РїР°СЂСЃРёРЅРі СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ.
- РџСЂРѕРІРµСЂРєР° СЏР·С‹РєР° docstring (Р°РЅРіР»РёР№СЃРєРёР№).
- РћРіСЂР°РЅРёС‡РµРЅРёРµ РґР»РёРЅС‹ С„СѓРЅРєС†РёРё.
- РџСЂРѕРјРµР¶СѓС‚РѕС‡РЅРѕРµ СЃРѕС…СЂР°РЅРµРЅРёРµ (checkpoint) РєР°Р¶РґС‹Рµ SAVE_EVERY СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ.
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

DetectorFactory.seed = 0  # РґР»СЏ СЃС‚Р°Р±РёР»СЊРЅРѕСЃС‚Рё langdetect

# ========== РќРђРЎРўР РћР™РљР ==========
TOKENS = [
    token.strip()
    for token in os.getenv("GITHUB_TOKENS", os.getenv("GITHUB_TOKEN", "")).split(",")
    if token.strip()
]

if not TOKENS:
    raise RuntimeError("Set GITHUB_TOKEN or comma-separated GITHUB_TOKENS before running this script.")
OUTPUT_FILE = "functions_with_docstrings.parquet"
CHECKPOINT_DIR = "checkpoints"
REPOS_TARGET = 10000         # СЃРєРѕР»СЊРєРѕ СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ С…РѕС‚РёРј РѕР±СЂР°Р±РѕС‚Р°С‚СЊ
PER_PAGE = 100              # GitHub API max per_page
PAGES_PER_QUERY = 10        # РѕР±С‹С‡РЅРѕ РґРѕ 10 СЃС‚СЂР°РЅРёС† (1000) вЂ” РЅРѕ РјС‹ СЂР°Р·Р±РёРІР°РµРј РїРѕ РґР°С‚Р°Рј
MAX_FILES_PER_REPO = 100
MAX_CODE_TOKENS = 500       # Р»РёРјРёС‚ СЃР»РѕРІ РІ РєРѕРґРµ С„СѓРЅРєС†РёРё
MAX_WORKERS = 16            # РїРѕС‚РѕРєРё РґР»СЏ РєР»РѕРЅРёСЂРѕРІР°РЅРёСЏ/РїР°СЂСЃРёРЅРіР°
SAVE_EVERY = 1000             # СЃРѕС…СЂР°РЅСЏС‚СЊ РїСЂРѕРјРµР¶СѓС‚РѕС‡РЅРѕ РєР°Р¶РґС‹Рµ N СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ
GITHUB_SEARCH_SLEEP = 1.2   # РїР°СѓР·Р° РјРµР¶РґСѓ Р·Р°РїСЂРѕСЃР°РјРё РїРѕРёСЃРєР° (СЃРµРє)

# Р Р°Р·Р±РёРІР°РµРј РїРѕ РґРёР°РїР°Р·РѕРЅР°Рј РґР°С‚ (created:) - СЃРїРёСЃРѕРє РєРѕСЂС‚РµР¶РµР№ (start, end)
# РџРѕРґР±РµСЂРёС‚Рµ РїРµСЂРёРѕРґС‹ С‚Р°Рє, С‡С‚РѕР±С‹ РІ РєР°Р¶РґРѕРј РґРёР°РїР°Р·РѕРЅРµ Р±С‹Р»Рѕ <=1000 СЂРµР·СѓР»СЊС‚Р°С‚РѕРІ.
# РџСЂРёРјРµСЂ: РїРѕ РіРѕРґР°Рј (РЅР°Р±РёСЂР°РµРј СЃС‚РѕР»СЊРєРѕ РґРёР°РїР°Р·РѕРЅРѕРІ, СЃРєРѕР»СЊРєРѕ РЅСѓР¶РЅРѕ)
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
# РљРѕСЂСЂРµРєС‚РёСЂСѓР№С‚Рµ DATE_RANGES, РїРѕРєР° РЅРµ РЅР°РєРѕРїРёС‚Рµ REPOS_TARGET СЂРµРїРѕ.

# =================================

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# ========== РЈС‚РёР»РёС‚С‹ ==========
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

# ========== РџР°СЂСЃРµСЂ С„СѓРЅРєС†РёР№ ==========
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

# ========== РљР»РѕРЅРёСЂРѕРІР°РЅРёРµ Рё РїР°СЂСЃРёРЅРі СЂРµРїРѕ ==========
def process_repository_clone(repo_url, max_files=MAX_FILES_PER_REPO):
    """РљР»РѕРЅРёСЂСѓРµС‚ СЂРµРїРѕ (С€allow depth=1) Рё РїР°СЂСЃРёС‚ .py С„Р°Р№Р»С‹. Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє Р·Р°РїРёСЃРµР№."""
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
                        # РґРѕР±Р°РІРёРј РєРѕРЅС‚РµРєСЃС‚ СЂРµРїРѕ/file РґР»СЏ РєР°Р¶РґРѕРіРѕ
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

# ========== РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ СЃР±РѕСЂ СЃРїРёСЃРєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ (СЃ РїР°РіРёРЅР°С†РёРµР№ Рё РґР°С‚Р°РјРё) ==========
async def fetch_repos_for_range(session, start_date, end_date, token, per_page=PER_PAGE, pages=PAGES_PER_QUERY):
    """Р—Р°РїСЂРѕСЃ search/repositories РґР»СЏ РґРёР°РїР°Р·РѕРЅР° created: start..end. Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє clone_url."""
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
                # РµСЃР»Рё rate limit, РїРѕРїС‹С‚РєР° РѕР¶РёРґР°С‚СЊ
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
        # РѕР±С…РѕРґРёРј РґРёР°РїР°Р·РѕРЅС‹ РґР°С‚
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
            # РЅРµР±РѕР»СЊС€Р°СЏ РїР°СѓР·Р° РјРµР¶РґСѓ РґРёР°РїР°Р·РѕРЅР°РјРё
            await asyncio.sleep(0.5)
            # Р·Р°С‰РёС‚Р° РѕС‚ СЃР»РёС€РєРѕРј Р±С‹СЃС‚СЂРѕР№ СЂР°Р±РѕС‚С‹
            if len(repo_urls) >= target_count:
                break
    return repo_urls

# ========== РћСЃРЅРѕРІРЅРѕР№ workflow ==========
async def main():
    print("=== Start collecting repo URLs ===")
    repo_urls = await gather_repo_urls(REPOS_TARGET)
    print(f"Found {len(repo_urls)} repo URLs; preparing to clone and parse.")

    # checkpoint: РµСЃР»Рё СѓР¶Рµ РµСЃС‚СЊ С„Р°Р№Р» СЃ РѕР±СЂР°Р±РѕС‚Р°РЅРЅС‹РјРё СЂРµРїРѕ вЂ” Р·Р°РіСЂСѓР·РёРј, С‡С‚РѕР±С‹ РЅРµ РґСѓР±Р»РёСЂРѕРІР°С‚СЊ
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
