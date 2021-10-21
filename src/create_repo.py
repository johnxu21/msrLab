import requests
import json

url = 'https://api.github.com/user/repos'
token = ''

headers = {'Authorization' : 'token {}'.format(token)}
ResporitoryName = input("Enter repo: ")

data = {'name' : '{}'.format(ResporitoryName)}

print(requests.post(url, data=json.dumps(data), headers=headers))