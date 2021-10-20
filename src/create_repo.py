import requests
import json

url = "https://api.github.com/kuyesu/repos"
token = "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"

headers = {"Authorization" : "token {}".format(token)}
RespositoryName = input("Enter the repo: ")

data = {"data" : "{}".format(RespositoryName)}

requests.post(url, data = json.dumps(data), headers=headers)
