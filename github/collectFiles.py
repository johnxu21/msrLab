import requests
import json
# Create your views here.

def github_auth(url, lstoken, ct):
    jsonData = None
     
    try:
        ct = ct % len(lstoken)
        request = requests.get(url, headers={'Authorization': 'token {}'.format(lstoken[ct])})
        jsonData = json.loads(request.content)
        
        ct += 1
        
    except Exception as e:
        print(e)
        print('Error: {}'.format(url))
    
    return jsonData, ct

def countFiles(dictfiles, lstoken, repo):
    ct = 0
    ipage = 1
    
    try:
        while True:
            spage = str(ipage)
            commitUrl = 'https://api.github.com/repos/{}/commits?page={}&per_page=100'.format(repo, spage)
            jsonCommits, ct = github_auth(commitUrl, lstoken, ct)
            
            if not jsonCommits:
                break
            
            for shaObjects in jsonCommits:
                sha = shaObjects['sha']
                shaUrl = 'https://api.github.com/repos/' + repo + '/git/commits/' + sha
                shaDetails, ct = github_auth(shaUrl, lstoken, ct)
                filesjson = shaDetails['files']
                for filenameObjects in filesjson:
                    filename = filenameObjects['filename']
                    if filename in dictfiles:
                        dictfiles[filename] += 1
                    else:
                        dictfiles[filename] = 1
                ipage += 1
    except Exception as e:
        print(e)
        print('Error: {}'.format(commitUrl))
    
    return dictfiles
    
   

