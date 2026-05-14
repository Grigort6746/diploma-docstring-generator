#!/usr/bin/env python3
"""
collect_github_dataset_v3.py
---------------------------------
РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ СЃР±РѕСЂ Python-СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ СЃ GitHub.
РР·РІР»РµС‡РµРЅРёРµ С„СѓРЅРєС†РёР№ СЃ Google-style docstrings.
РџРѕРґРґРµСЂР¶РєР°:
- Р РѕС‚Р°С†РёСЏ С‚РѕРєРµРЅРѕРІ
- РџР°РіРёРЅР°С†РёСЏ + СЂР°Р·РЅС‹Рµ РґРёР°РїР°Р·РѕРЅС‹ stars
- РџСЂРѕРїСѓСЃРє СѓР¶Рµ СЃРѕР±СЂР°РЅРЅС‹С… СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ
- РџСЂРѕРјРµР¶СѓС‚РѕС‡РЅС‹Рµ СЃРѕС…СЂР°РЅРµРЅРёСЏ
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

DetectorFactory.seed = 0  # СЃС‚Р°Р±РёР»СЊРЅРѕСЃС‚СЊ langdetect

# ========== РќРђРЎРўР РћР™РљР ==========

TOKENS = [
    token.strip()
    for token in os.getenv("GITHUB_TOKENS", os.getenv("GITHUB_TOKEN", "")).split(",")
    if token.strip()
]

if not TOKENS:
    raise RuntimeError("Set GITHUB_TOKEN or comma-separated GITHUB_TOKENS before running this script.")

OUTPUT_FILE = "functions_with_docstrings_4.parquet"
CHECKPOINT_DIR = "checkpoints"
REPOS_TARGET = 1000          # СЃРєРѕР»СЊРєРѕ СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ РѕР±СЂР°Р±РѕС‚Р°С‚СЊ
PER_PAGE = 100               # РјР°РєСЃРёРјСѓРј 100
PAGES = 10                   # РјР°РєСЃРёРјСѓРј 10 (1000 СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ)
MAX_FILES_PER_REPO = 100     # РјР°РєСЃРёРјСѓРј .py С„Р°Р№Р»РѕРІ
MAX_CODE_TOKENS = 300        # Р»РёРјРёС‚ СЃР»РѕРІ РІ РєРѕРґРµ
MAX_WORKERS = 12             # РїРѕС‚РѕРєРё РґР»СЏ РєР»РѕРЅРёСЂРѕРІР°РЅРёСЏ
SAVE_EVERY = 100             # СЃРѕС…СЂР°РЅСЏС‚СЊ РєР°Р¶РґС‹Рµ N СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ
SLEEP_BETWEEN_PAGES = 1.2    # РїР°СѓР·Р° РјРµР¶РґСѓ Р·Р°РїСЂРѕСЃР°РјРё
LANGUAGE = "python"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# ========== Р’РЎРџРћРњРћР“РђРўР•Р›Р¬РќР«Р• Р¤РЈРќРљР¦РР ==========

def rotate_token(index: int) -> str:
    return TOKENS[index % len(TOKENS)]

def is_google_style_docstring(docstring: str) -> bool:
    return bool(docstring and "Args:" in docstring and "Returns:" in docstring)

def safe_detect_lang(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"

# ========== РР—Р’Р›Р•Р§Р•РќРР• Р¤РЈРќРљР¦РР™ РР— Р¤РђР™Р›Рђ ==========

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

# ========== РљР›РћРќРР РћР’РђРќРР• Р РџРђР РЎРРќР“ Р Р•РџРћР—РРўРћР РРЇ ==========

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

# ========== РЎР‘РћР  URL Р Р•РџРћР—РРўРћР РР•Р’ (СЃ РґРёР°РїР°Р·РѕРЅР°РјРё stars) ==========

def generate_star_queries():
    """Р Р°Р·РЅС‹Рµ РґРёР°РїР°Р·РѕРЅС‹ РїРѕРїСѓР»СЏСЂРЅРѕСЃС‚Рё, С‡С‚РѕР±С‹ РѕР±РѕР№С‚Рё Р»РёРјРёС‚ 1000 СЂРµР·СѓР»СЊС‚Р°С‚РѕРІ."""
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
            print(f"вљ пёЏ РћС€РёР±РєР° {resp.status} РґР»СЏ {query}, СЃС‚СЂ. {page}: {text[:100]}")
            if resp.status == 403:
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset:
                    sleep_for = max(10, int(reset) - int(time.time()) + 5)
                    print(f"вЏі РџСЂРµРІС‹С€РµРЅ Р»РёРјРёС‚. Р–РґС‘Рј {sleep_for} СЃРµРє...")
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

# ========== РћРЎРќРћР’РќРћР™ WORKFLOW ==========

async def main():
    print("рџ”№ РќР°С‡РёРЅР°РµРј СЃР±РѕСЂ СЃРїРёСЃРєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ...")

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
    print(f"рџ“¦ РЈР¶Рµ СЃРѕР±СЂР°РЅРѕ {len(processed_set)} СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ (Р±СѓРґСѓС‚ РїСЂРѕРїСѓС‰РµРЅС‹).")

    repo_urls = await gather_repo_urls_with_queries(processed_set, REPOS_TARGET)
    print(f"вњ… РќР°Р№РґРµРЅРѕ {len(repo_urls)} РЅРѕРІС‹С… СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ РґР»СЏ РѕР±СЂР°Р±РѕС‚РєРё.")

    accumulated = []
    partial_parquet = os.path.join(CHECKPOINT_DIR, "partial_results.parquet")
    if os.path.exists(partial_parquet):
        try:
            df_existing = pd.read_parquet(partial_parquet)
            accumulated = df_existing.to_dict(orient="records")
            print(f"рџ“‚ Р—Р°РіСЂСѓР¶РµРЅРѕ {len(accumulated)} Р·Р°РїРёСЃРµР№ РёР· checkpoint.")
        except Exception:
            print("вљ пёЏ РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё checkpoint, РЅР°С‡РёРЅР°РµРј Р·Р°РЅРѕРІРѕ.")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [(repo_url, executor.submit(process_repository_clone, repo_url)) for repo_url in repo_urls]

        processed_counter = 0
        for repo_url, fut in tqdm(futures, desc="рџ”Ќ РћР±СЂР°Р±РѕС‚РєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ"):
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
                    print(f"рџ’ѕ Checkpoint: СЃРѕС…СЂР°РЅРµРЅРѕ {len(df)} Р·Р°РїРёСЃРµР№.")

    df_final = pd.DataFrame(accumulated)
    if not df_final.empty:
        df_final = df_final.drop_duplicates(subset=["code"])
        df_final.to_parquet(OUTPUT_FILE, index=False)
        print(f"вњ… Р“РѕС‚РѕРІРѕ. РЎРѕС…СЂР°РЅРµРЅРѕ {len(df_final)} Р·Р°РїРёСЃРµР№ РІ {OUTPUT_FILE}")
    else:
        print("вљ пёЏ РќРµ РЅР°Р№РґРµРЅРѕ С„СѓРЅРєС†РёР№. РџСЂРѕРІРµСЂСЊ С„РёР»СЊС‚СЂС‹ РёР»Рё С‚РѕРєРµРЅС‹.")

if __name__ == "__main__":
    asyncio.run(main())
