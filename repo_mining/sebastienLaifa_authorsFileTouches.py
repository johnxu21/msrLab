import json
import requests
import csv
import os
from dotenv import load_dotenv

load_dotenv()

if not os.path.exists("data"):
    os.makedirs("data")

# GitHub Authentication function
def github_auth(url, lsttokens, ct):
    jsonData = None
    try:
        ct = ct % len(lsttokens)
        headers = {'Authorization': 'Bearer {}'.format(lsttokens[ct])}
        request = requests.get(url, headers=headers)
        jsonData = json.loads(request.content)
        ct += 1
    except Exception as e:
        print(e)
    return jsonData, ct

# Write touches per author per file
def collect_file_touches(lsttokens, repo):
    ipage = 1
    ct = 0 

    touches = []  # list of dicts with Filename, Author, Date

    try:
        while True:
            spage = str(ipage)
            commitsUrl = f'https://api.github.com/repos/{repo}/commits?page={spage}&per_page=100'
            jsonCommits, ct = github_auth(commitsUrl, lsttokens, ct)

            if not jsonCommits or len(jsonCommits) == 0:
                break

            for shaObject in jsonCommits:
                sha = shaObject['sha']
                shaUrl = f'https://api.github.com/repos/{repo}/commits/{sha}'
                shaDetails, ct = github_auth(shaUrl, lsttokens, ct)

                if not shaDetails or "files" not in shaDetails:
                    continue

                author = None
                date = None
                if shaDetails.get("commit"):
                    commit_info = shaDetails["commit"]
                    author = commit_info["author"]["name"]
                    date = commit_info["author"]["date"]

                filesjson = shaDetails["files"]
                for filenameObj in filesjson:
                    filename = filenameObj["filename"]
                    if filename.endswith((".java", ".kt")):
                        touches.append({
                            "Filename": filename,
                            "Author": author,
                            "Date": date
                        })

            ipage += 1

    except Exception as e:
        print("Error receiving data:", e)
        exit(0)

    return touches


# GitHub repo
repo = "scottyab/rootbeer"
lstTokens = [os.getenv("GITHUB_TOKEN")]

# Collect per-touch info
touches = collect_file_touches(lstTokens, repo)

# Write to CSV
output_file = "data/authors_file_touches.csv"
with open(output_file, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["Filename", "Author", "Date"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(touches)
