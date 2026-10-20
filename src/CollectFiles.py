import json
import requests
import csv
import sys

import os

# Read the GitHub token from the environment instead of hardcoding it.
# Set it in your terminal before running, e.g.  export GITHUB_TOKEN=your_token_here
# Never put a real token in this file or commit it to GitHub.
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

# GitHub Authentication function
# Sends one GET request to the GitHub API and returns the parsed JSON.
# Returns None if the request or the JSON parsing fails (the error is printed).
def github_auth(url):
    jsonData = None
    try:
        # The token goes in the Authorization header so GitHub knows who is asking
        headers = {'Authorization': 'Bearer {}'.format(GITHUB_TOKEN)}
        request = requests.get(url, headers=headers)
        # request.content holds the raw response body; json.loads turns it into Python lists/dicts
        jsonData = json.loads(request.content)
    except Exception as e:
        print(e)
    return jsonData

# @dictFiles, empty dictionary of files (filename -> number of commits that touched it)
# @repo, GitHub repo, in the form 'owner/name'
def countfiles(dictfiles, repo):
    ipage = 1  # url page counter

    try:
        # loop though all the commit pages until the last returned empty page
        while True:
            spage = str(ipage)
            commitsUrl = 'https://api.github.com/repos/' + repo + '/commits?page=' + spage + '&per_page=100'
            jsonCommits = github_auth(commitsUrl)

            # break out of the while loop if there are no more commits in the pages
            if len(jsonCommits) == 0:
                break
            # iterate through the list of commits in  spage
            for shaObject in jsonCommits:
                # Each commit has a unique id called a sha
                sha = shaObject['sha']
                # For each commit, use the GitHub commit API to extract the files touched by the commit
                shaUrl = 'https://api.github.com/repos/' + repo + '/commits/' + sha
                shaDetails = github_auth(shaUrl)
                filesjson = shaDetails['files']
                # Add 1 to the count for each file this commit touched
                for filenameObj in filesjson:
                    filename = filenameObj['filename']
                    dictfiles[filename] = dictfiles.get(filename, 0) + 1
                    print(filename)
            ipage += 1
    except:
        # Any unexpected error (for example, a bad token or a rate limit) ends the script here
        print("Error receiving data")
        sys.exit(1)

# GitHub repo
# To analyze a different project, change this line to 'owner/name' (the part after github.com/)
# Only one repo line should be active at a time
repo = 'scottyab/rootbeer'
# repo = 'Skyscanner/backpack' # This repo is commit heavy. It takes long to finish executing
# repo = 'k9mail/k-9' # This repo is commit heavy. It takes long to finish executing
# repo = 'mendhak/gpslogger'


def main():
    # Stop before doing any work if no token was given
    if not GITHUB_TOKEN:
        sys.stderr.write("Error: set the GITHUB_TOKEN environment variable before running this script.\n")
        sys.exit(1)

    # Create the data/ folder for the CSV output if it does not exist yet
    if not os.path.exists("data"):
        os.makedirs("data")

    # Collect the file counts; dictfiles is filled in by countfiles
    dictfiles = dict()
    countfiles(dictfiles, repo)
    print('Total number of files: ' + str(len(dictfiles)))

    # Build the output file name from the repo name, e.g. 'rootbeer' -> data/file_rootbeer.csv
    file = repo.split('/')[1]
    # change this to the path of your file
    fileOutput = 'data/file_' + file + '.csv'
    rows = ["Filename", "Touches"]
    fileCSV = open(fileOutput, 'w')
    writer = csv.writer(fileCSV)
    # Write the header row first
    writer.writerow(rows)

    # Track the file with the highest count while writing one row per file
    bigcount = None
    bigfilename = None
    for filename, count in dictfiles.items():
        rows = [filename, count]
        writer.writerow(rows)
        if bigcount is None or count > bigcount:
            bigcount = count
            bigfilename = filename
    fileCSV.close()
    # bigfilename stays None when the repo has no files, so report that instead of crashing
    if bigfilename is None:
        print('No files were found for ' + repo)
    else:
        print('The file ' + bigfilename + ' has been touched ' + str(bigcount) + ' times.')


# Run main() only when this file is executed directly, not when a test imports it
if __name__ == "__main__":
    main()
