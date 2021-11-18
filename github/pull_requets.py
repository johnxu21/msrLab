import requests
import pandas as pd
# from matplotlib import pyplot as plt

base_url = 'https://api.github.com/repos/{}/pulls?state=all'
repos = ['scotyab/rootbeer', 'Skyscanner/backpack', 'k9mail/k-9', 'mendhak/gpslogger', 'PeterlJia/android_xlight']
def get_pull_requests(repos):

    counter = 0
    for repo in repos:
        response = requests.get(base_url.format(repo))
        if response.status_code == 200:
            pull_requests = response.json()
            print(" {} has {} pull requests ".format(repo, len(pull_requests)))
            print("{} merged pulls".format(len([
                pr for pr in pull_requests
                    if pr['merged_at'] is not None
            ])))
            print('{} closed pull_requests'.format(len([
                pr for pr in pull_requests
                    if pr['closed_at'] is not None and pr['merged_at'] is None
            ])))
            print('{} open pull requests'.format(len([
                pr for pr in pull_requests
                    if pr['closed_at'] is None and pr['merged_at'] is not None
            ])))
            
            pull_info = []
            pull_info.append(pull_requests)
            counter +=1

    dataframe = pd.DataFrame(columns=['created_at', 'merged_at', 'closed_at', 'repo', 'title', 'author', 'state'])
    for data_in_repo in pull_info:
        for pull_request in data_in_repo:
            dataframe = dataframe.append({
                'repo': pull_request['base']['repo']['name'],
                'state':pull_request['state'],
                'merged_at':pull_request['merged_at'],
                'closed_at':pull_request['closed_at'],
                'created_at':pull_request['created_at']
            }, ignore_index= True)

    for col in ['merged_at', 'closed_at' , 'created_at']:
        dataframe[col] = pd.to_datetime(dataframe[col], format='%Y-%m-%dT%H:%M:%SZ')

    merged_data_frame = dataframe[dataframe['merged_at'].notnull()]
    closed_data_frame = dataframe[dataframe['closed_at'].notnull() & dataframe['merged_at'].isnull()]
    
    return merged_data_frame, closed_data_frame
