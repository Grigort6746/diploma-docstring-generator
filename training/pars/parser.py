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

DetectorFactory.seed = 0  # стабильность детекции языка

# === НАСТРОЙКИ ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
OUTPUT_FILE = "functions_with_docstrings.parquet"
REPOS_LIMIT = 20000          # общее количество репозиториев для обработки
MAX_FILES_PER_REPO = 100   # максимум Python-файлов из одного репо
MAX_WORKERS = 16           # количество потоков для парсинга
MAX_CODE_TOKENS = 600      # ограничение по длине функции
PAGES = 200                 # количество страниц GitHub API (до 1000 репозиториев)

# === 1. Проверка Google-style docstring ===
def is_google_style_docstring(docstring: str) -> bool:
    if not docstring:
        return False
    docstring = docstring.strip()
    return "Args:" in docstring and "Returns:" in docstring

# === 2. Извлечение функций из одного файла ===
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

            # Проверяем язык docstring
            try:
                if detect(doc) != "en":
                    continue
            except Exception:
                continue

            # Получаем код функции
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

# === 3. Асинхронная загрузка списка репозиториев с GitHub ===
async def fetch_repo_urls(pages: int = PAGES, per_page: int = 100):
    """Асинхронно получает до 1000 Python-репозиториев по звёздам."""
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
                    print(f"⚠️ Ошибка загрузки страницы {page}: {resp.status}")
                    continue
                data = await resp.json()
                new_urls = [item["clone_url"] for item in data.get("items", [])]
                urls.extend(new_urls)
                await asyncio.sleep(2)  # пауза для избежания rate limit

    print(f"🔍 Найдено {len(urls)} репозиториев")
    return urls[:REPOS_LIMIT]

# === 4. Парсинг одного репозитория ===
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

# === 5. Асинхронный сбор данных ===
async def collect_from_github():
    repo_urls = await fetch_repo_urls()
    all_data = []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = [loop.run_in_executor(executor, process_repository, url) for url in repo_urls]

        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="⚙️ Обработка репозиториев"):
            try:
                result = await future
                all_data.extend(result)
            except Exception:
                continue

    return all_data

# === 6. Основная функция ===
async def main():
    data = await collect_from_github()
    print(f"✅ Собрано {len(data)} функций с Google-style docstring (EN)")

    if not data:
        print("❌ Нет данных. Проверь токен или интернет.")
        return

    df = pd.DataFrame(data)
    df.drop_duplicates(subset=["code"], inplace=True)
    df.to_parquet(OUTPUT_FILE, index=False)
    print(f"💾 Сохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
