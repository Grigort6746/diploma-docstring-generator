import os
import re
import ast
import tempfile
import aiohttp
import asyncio
import pandas as pd
from tqdm.asyncio import tqdm
from git import Repo
from langdetect import detect, DetectorFactory
from concurrent.futures import ThreadPoolExecutor

DetectorFactory.seed = 0  # СЃС‚Р°Р±РёР»СЊРЅРѕСЃС‚СЊ РґРµС‚РµРєС†РёРё СЏР·С‹РєР°

# === РќРђРЎРўР РћР™РљР ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
OUTPUT_FILE = "functions_with_docstrings.parquet"
REPOS_LIMIT = 20000          # РѕР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ РґР»СЏ РѕР±СЂР°Р±РѕС‚РєРё
MAX_FILES_PER_REPO = 100   # РјР°РєСЃРёРјСѓРј Python-С„Р°Р№Р»РѕРІ РёР· РѕРґРЅРѕРіРѕ СЂРµРїРѕ
MAX_WORKERS = 16           # РєРѕР»РёС‡РµСЃС‚РІРѕ РїРѕС‚РѕРєРѕРІ РґР»СЏ РїР°СЂСЃРёРЅРіР°
MAX_CODE_TOKENS = 600      # РѕРіСЂР°РЅРёС‡РµРЅРёРµ РїРѕ РґР»РёРЅРµ С„СѓРЅРєС†РёРё
PAGES = 200                 # РєРѕР»РёС‡РµСЃС‚РІРѕ СЃС‚СЂР°РЅРёС† GitHub API (РґРѕ 1000 СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ)

# === 1. РџСЂРѕРІРµСЂРєР° Google-style docstring ===
def is_google_style_docstring(docstring: str) -> bool:
    if not docstring:
        return False
    docstring = docstring.strip()
    return "Args:" in docstring and "Returns:" in docstring

# === 2. РР·РІР»РµС‡РµРЅРёРµ С„СѓРЅРєС†РёР№ РёР· РѕРґРЅРѕРіРѕ С„Р°Р№Р»Р° ===
def extract_functions(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src)
    except Exception:
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if not (doc and is_google_style_docstring(doc)):
                continue

            # РџСЂРѕРІРµСЂСЏРµРј СЏР·С‹Рє docstring
            try:
                if detect(doc) != "en":
                    continue
            except Exception:
                continue

            # РџРѕР»СѓС‡Р°РµРј РєРѕРґ С„СѓРЅРєС†РёРё
            try:
                code = ast.get_source_segment(src, node)
                if not code or len(code.split()) > MAX_CODE_TOKENS:
                    continue

                results.append({
                    "function_name": node.name,
                    "code": code.strip(),
                    "docstring": doc.strip().replace("\r", "").replace("\n\n", "\n")
                })
            except Exception:
                continue
    return results

# === 3. РђСЃРёРЅС…СЂРѕРЅРЅР°СЏ Р·Р°РіСЂСѓР·РєР° СЃРїРёСЃРєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ СЃ GitHub ===
async def fetch_repo_urls(pages: int = PAGES, per_page: int = 100):
    """РђСЃРёРЅС…СЂРѕРЅРЅРѕ РїРѕР»СѓС‡Р°РµС‚ РґРѕ 1000 Python-СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ РїРѕ Р·РІС‘Р·РґР°Рј."""
    if not GITHUB_TOKEN:
        raise RuntimeError("Set the GITHUB_TOKEN environment variable before running this script.")

    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    urls = []

    async with aiohttp.ClientSession(headers=headers) as session:
        for page in range(1, pages + 1):
            api_url = (
                f"https://api.github.com/search/repositories"
                f"?q=language:python+stars:>100+size:<50000"
                f"&sort=stars&per_page={per_page}&page={page}"
            )
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    print(f"вљ пёЏ РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё СЃС‚СЂР°РЅРёС†С‹ {page}: {resp.status}")
                    continue
                data = await resp.json()
                new_urls = [item["clone_url"] for item in data.get("items", [])]
                urls.extend(new_urls)
                await asyncio.sleep(2)  # РїР°СѓР·Р° РґР»СЏ РёР·Р±РµР¶Р°РЅРёСЏ rate limit

    print(f"рџ”Ќ РќР°Р№РґРµРЅРѕ {len(urls)} СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ")
    return urls[:REPOS_LIMIT]

# === 4. РџР°СЂСЃРёРЅРі РѕРґРЅРѕРіРѕ СЂРµРїРѕР·РёС‚РѕСЂРёСЏ ===
def process_repository(repo_url):
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            Repo.clone_from(repo_url, tmpdir, depth=1)
        except Exception:
            return []

        file_count = 0
        for root, _, files in os.walk(tmpdir):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    results.extend(extract_functions(path))
                    file_count += 1
                    if file_count >= MAX_FILES_PER_REPO:
                        break
            if file_count >= MAX_FILES_PER_REPO:
                break

    return results

# === 5. РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ СЃР±РѕСЂ РґР°РЅРЅС‹С… ===
async def collect_from_github():
    repo_urls = await fetch_repo_urls()
    all_data = []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = [loop.run_in_executor(executor, process_repository, url) for url in repo_urls]

        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="вљ™пёЏ РћР±СЂР°Р±РѕС‚РєР° СЂРµРїРѕР·РёС‚РѕСЂРёРµРІ"):
            try:
                result = await future
                all_data.extend(result)
            except Exception:
                continue

    return all_data

# === 6. РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ ===
async def main():
    data = await collect_from_github()
    print(f"вњ… РЎРѕР±СЂР°РЅРѕ {len(data)} С„СѓРЅРєС†РёР№ СЃ Google-style docstring (EN)")

    if not data:
        print("вќЊ РќРµС‚ РґР°РЅРЅС‹С…. РџСЂРѕРІРµСЂСЊ С‚РѕРєРµРЅ РёР»Рё РёРЅС‚РµСЂРЅРµС‚.")
        return

    df = pd.DataFrame(data)
    df.drop_duplicates(subset=["code"], inplace=True)
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"рџ’ѕ РЎРѕС…СЂР°РЅРµРЅРѕ РІ {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
