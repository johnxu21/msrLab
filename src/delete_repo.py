import requests
import json



token = ''

headers = {'Authorization' : 'token {}'.format(token)}

username = input("Enter the username: ")
ResporitoryName = input("Enter the repo name: ")

url = 'https://api.github.com/repos/{}/{}'.format(username,ResporitoryName)

try:
    
    requests.delete(url, headers=headers)
    print("succesfully created the {}".format(ResporitoryName))
    
except Exception as e:
    print("unsuccesfully {}\n {}".format(ResporitoryName, e))
    
# return requests.delete(url, headers=headers)