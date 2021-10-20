import json
from pip._vendor import requests
import csv


# repo = 'kuyesu/sre'
# put your tokens here
lstTokens = []
# GitHub Authentication function
def github_auth(url, lsttoken, ct):
    jsonData = None
    try:
        ct = ct % len(lstTokens)
        headers = {'Authorization': 'Bearer {}'.format(lsttoken[ct])}
        request = requests.get(url, headers=headers)
        jsonData = json.loads(request.content)
        ct += 1
    except Exception as e:
        pass
        print(e)
    return jsonData, ct

# @dictFiles empty dictionary of files
# @lstTokens GitHub authentication tokens
def countfiles( lsttokens, repo, filenames, names, dates):
    ipage = 1  # url page counter
    ct = 0  # token counter
    try:
        print("Rogers here, passed test 1")
        # loop though all the commit pages until the last returned empty page
        while True:
            print("Rogers here, passed test while loop")
            if ct == len(lstTokens):
                ct = 0
            spage = str(ipage)
            # commitsUrl = 'https://api.github.com/repos/' + repo + '/commits?page=' + spage + \
            #              '&per_page=100&access_token=' + lsttokens[ct]
            commitsUrl = 'https://api.github.com/repos/' + repo + '/commits?page=' + spage + '&per_page=100'
            jsonCommits, ct = github_auth(commitsUrl, lsttokens, ct)
            
            
            ct += 1
            print("Rogers here, passed test 2")
            print("Rogers here, passed test 1")
            content = requests.get(commitsUrl)
            print("Rogers here, passed test 3")
            # jsonCommits = json.loads(content.content)
            # break out of the while loop if there are no more commits in the pages
            print("Rogers here, passed test 4")
            print("Rogers here, passed test 5")
            if len(jsonCommits) == 0:
                break
            # iterate through the list of commits in a page
            for shaObject in jsonCommits:
                print("Rogers here, passed test 6")
                sha = shaObject['sha']
                print("Rogers here, passed test 7")
                if ct == len(lstTokens):
                    print("Rogers here, passed test 8")
                    ct = 0
                # For each commit, use the GitHub commit API to extract the files touched by the commit
                print("Rogers here, passed test 9")
                shaUrl = 'https://api.github.com/repos/' + repo + '/commits/' + sha
                shaDetails, ct = github_auth(shaUrl, lsttokens, ct)
                
                print("Rogers here, passed test 10")
                ct += 1
                
                
                             
                # content = requests.get(shaUrl)
                # shaDetails = json.loads(content.content)
                
                
                files = shaDetails['files']
                for file in files:
                    filename = file['filename']
                    if filename.endswith('.java'):
                        name = shaDetails['commit']['author']['name']
                        date = shaDetails['commit']['author']['date']
                        names.append(name)
                        dates.append(date)
                        filenames.append(filename)
            ipage += 1
    except:
        print("Rogers correct from here 'exception'")
        print("Error receiving data")
        exit(0)

repo = 'kuyesu/rootbeer'
# put your tokens here
lstTokens = ['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']

names = []
dates = []
dictfiles = dict()
filenames = []
countfiles(lstTokens, repo, filenames, names, dates)
print('Total number of files: ' + str(len(dictfiles)))


file = repo.split('/')[1]
#change this to the path of your file
fileOutput = 'data/file_' + file + '.csv' #/Users/businge/Documents/00Mercy/sre2020/file_'+file+'.csv'
rows = ["Filename", "Author", "Date"]
fileCSV = open(fileOutput, 'w')
writer = csv.writer(fileCSV)
writer.writerow(rows)

iterator = 0;
for filename in filenames:
    rows = [filename,  names[iterator], dates[iterator]]
    iterator+=1
    writer.writerow(rows)
fileCSV.close()