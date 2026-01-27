import os 
import json
import time 
import requests

OWNER = 'scottyab'
REPO = 'rootbeer'
REPOFULL = f'{OWNER}/{REPO}'

TOKEN = os.getenv('GITHUB_TOKEN', '')

HEADERS = {}

if TOKEN:
    HEADERS = {'Authorization': f'token {TOKEN}'}

"""
    returns lists of all commit objects from 
    GITHUB API for a single file path
"""
def getCommits(path: str):
    url = f"https://api.github.com/repos/{REPOFULL}/commits"
    params = {'path': path, 'per_page': 100, 'page': 1}
    commits = []

    while True:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        page_data = r.json()
        if not page_data:
            break
        commits.extend(page_data)
        params["page"] += 1
        time.sleep(0.15) 
    return commits

def main():
    # Read the source files produced by Angel_CollectFiles.py
    with open("data/source_files.txt", "r", encoding="utf-8") as f:
        files = [line.strip() for line in f if line.strip()]

    touches = [] 

    for i, path in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] Getting commits for: {path}")
        commits = getCommits(path)

        for c in commits:
            commit_info = c.get("commit", {})
            author_block = commit_info.get("author", {}) or {}

            # use GitHub login when available or fall back to commit author name
            author_login = (c.get("author") or {}).get("login")
            author_name = author_block.get("name")
            author = author_login or author_name or "unknown"

            date_str = author_block.get("date")  
            if date_str:
                touches.append({
                    "file": path,
                    "author": author,
                    "date": date_str
                })

    os.makedirs("data", exist_ok=True)
    out_path = "data/file_touches.json"
    with open(out_path, "w", encoding="utf-8") as out:
        json.dump(touches, out, indent=2)

    print(f"\nWrote {len(touches)} touch records to {out_path}")

if __name__ == "__main__":
    main()