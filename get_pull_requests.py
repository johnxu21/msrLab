
'''
Write a script that will extract the merged pull requests and the closed (but not merged) 
from each of the repositories above. You can read about the structure of the pull 
requests from here  Pull Reuests. Draw one graph containing all the five repos above which 
compares merged pull requests and closed (but not merged).
'''
import requests
import pandas as pd
from matplotlib import pyplot as plt
# 
token = "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"
user_account = "jose-rodrigo-santos"
headers = {
        "Authorization": f"Bearer {token}"
    }

"""pull request query"""
pullRequestQuery = """
%s: search(query: "%s author:%s type:pr is:merged", type: ISSUE, first: 100) {
    issueCount
}
"""

userQuery = """
{
    account(login: "%s") {
        membersWithRole(first: 100) {
            nodes {
                login
            }
        }
    }
}

"""


pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'

# repos = ['facebook/react', 'facebook/react-native', 'facebook/react-native-web', 'facebook/react-native-scripts', 'facebook/react-native-renderer']
repos = ['scottyab/rootbeer','Skyscanner/backpack','k9mail/k-9','mendhak/gpslogger']
pull_info = []
pull_request_data = pull_info
def get_pull_requests(repo):
    """
    Get the pull requests from a repos
    """
    count = 0
    # for repo in repos:
    #     pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'
    #     pull_request_url = pull_request_url.format(repo)
    #     response = requests.get(pull_request_url, headers=headers)
    #     if response.status_code != 200:
    #         raise Exception('Error getting pull requests')
    #     pull_requests = response.json()
    #     print(pull_requests)
    # return pull_requests()
    for repo in repos:
        response = requests.get(pull_request_url.format(repo))
        if response.status_code == 200:
            pull_requests = response.json()
            print('{} has {} pull requests'.format(repo, len(pull_requests)))
            print('{} merged pull requests'.format(len([pr for pr in pull_requests if pr['merged_at'] is not None])))
            print('{} closed pull requests'.format(len([pr for pr in pull_requests if pr['closed_at'] is not None and pr['merged_at'] is None])))
            print('{} open pull requests'.format(len([pr for pr in pull_requests if pr['closed_at'] is None])))
            print('\n')
            pull_request_data.append(pull_requests)
            count += 1
            
            print(pull_request_data)
            print("Repos : " + str(count)+"/"+str(len(repos)))
            
   
    
    pull_request_df = pd.DataFrame(columns=['repo', 'state', 'merged_at', 'closed_at', 'created_at', 'author', 'title'])
    for repo_data in pull_request_data:
        for pull_request in repo_data:
            pull_request_df = pull_request_df.append({
                'repo': pull_request['base']['repo']['name'],
                'state': pull_request['state'],
                'merged_at': pull_request['merged_at'],
                'closed_at': pull_request['closed_at'],
                'created_at': pull_request['created_at'],
                # 'author': pull_request['author']['login'],
                
            }, ignore_index=True)

    # print(pull_request_df)
    for col in ['merged_at', 'closed_at', 'created_at']:
        pull_request_df[col] = pd.to_datetime(pull_request_df[col], format='%Y-%m-%dT%H:%M:%SZ')
    
        
        merged_pull_request_df = pull_request_df[pull_request_df['merged_at'].notnull()]
        closed_pull_request_df = pull_request_df[pull_request_df['closed_at'].notnull() & pull_request_df['merged_at'].isnull()]    
        merged_pull_request_df.to_csv(r""+'merged_pull_request.csv')
        closed_pull_request_df.to_csv(r""+'closed_pull_request.csv')
        
        
        # ax = merged_pull_request_df['created_at', 'merged_at',].plot(kind='bar',  title='Merged Pull Requests', figsize=(15, 10), legend=True, fontsize=12)
        
        
        # axes = plt.gca()
        # pull_request_df.plot(x = merged_pull_request_df['created_at'], y =  merged_pull_request_df['merged_at'])
        # # pull_request_df.plot(closed_pull_request_df['created_at'], closed_pull_request_df['closed_at'], kind='line', label='Closed', ax = axes )
        # axes.set_xlabel('Created at')
        # axes.set_ylabel('Closed at')  
        # axes.legend()
        # plt.show()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(merged_pull_request_df['created_at'], merged_pull_request_df['merged_at'],label='Merged')
        ax.plot(closed_pull_request_df['created_at'], closed_pull_request_df['closed_at'], label='Closed')
        ax.set_xlabel('Created at')
        ax.set_ylabel('Closed at')
        ax.set_title('Merged and closed pull requests')
        ax.legend()
        plt.show()
        
    #     if merged_pull_request_df & closed_pull_request_df:
            
    #         fig, ax = plt.subplots(figsize=(12, 6))
            
    #         merged_pull_request_df.to_csv(r""+'merged_pull_request.csv')
    #         closed_pull_request_df.to_csv(r""+'closed_pull_request.csv')
    #         merged_pull_request_df.plot(x='merged_at', y='closed_at', kind='scatter')
    #         plt.show()
        
    # else:
    #     print('No data')
        
    # print(pull_request_df)
    # return pull_request_df

get_pull_requests(repos)

    
    



# for repo in repos:
#     response = requests.get(pull_request_url.format(repo))
#     if response.status_code == 200:
#         pull_requests = response.json()
#         print('{} has {} pull requests'.format(repo, len(pull_requests)))
#         print('{} merged pull requests'.format(len([pr for pr in pull_requests if pr['merged_at'] is not None])))
#         print('{} closed pull requests'.format(len([pr for pr in pull_requests if pr['closed_at'] is not None and pr['merged_at'] is None])))
#         print('{} open pull requests'.format(len([pr for pr in pull_requests if pr['closed_at'] is None])))
#         print('\n')
# pull_info = []
# pull_request_data = pull_info['data']
# pull_request_df = pd.DataFrame(columns=['repo', 'state', 'merged_at', 'closed_at', 'created_at', 'author', 'title'])
# for repo_data in pull_request_data:
#     for pull_request in repo_data['pullRequests']:
#         pull_request_df = pull_request_df.append({
#             'repo': repo_data['name'],
#             'state': pull_request['state'],
#             'merged_at': pull_request['mergedAt'],
#             'closed_at': pull_request['closedAt'],
#             'created_at': pull_request['createdAt'],
#             'author': pull_request['author']['login'],
            
#         }, ignore_index=True)


# for col in ['merged_at', 'closed_at', 'created_at']:
#     pull_request_df[col] = pd.to_datetime(pull_request_df[col], utc=True)


# if merged_pull_request_df.notEmpty() and closed_pull_request_df.notEmpty():
#     merged_pull_request_df.to_csv(r""+'merged_pull_request.csv')
#     closed_pull_request_df.to_csv(r""+'closed_pull_request.csv')
#     merged_pull_request_df.plot(x='merged_at', y='closed_at', kind='scatter')
