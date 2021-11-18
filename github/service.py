import pandas as pd
class CollectFilesView(TemplateView):
    template_name = "collecFiles.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['files'] = countFiles()
        return context
    
    
    
    
    
    # def get_context_data(self, **kwargs):
    #     context = super(CollectFilesView, self).get_context_data(**kwargs)
    #     context['files'] = collectFiles()
    #     return context

    # def get_context_data(self, *args, **kwargs):
    # context = {
    #     'files': countFiles(dictfiles, lstoken, repo)
    # }
    # #     return context
    # lstoken = []
    # repo = ""
    # dictfiles = dict()
    
    # countFiles(dictfiles, lstoken, repo)
    # totalfiles = str(len(dictfiles))
    
    # fileName = None
    # fileCount = None
    
    # for filename, count in dictfiles.items():
    #     if fileCount > 1:
    #         fileCount = count
    #         fileName = filename
            
    # context = {
    #     'files': countFiles(dictfiles, lstoken, repo),
    # } 
    
    # context = {
        
    # }
    
    # return context
    
class Get_Pull_Requests(TemplateView):
    template_name = "github/get_pull_requests.html"
    
    # pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'
    # pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'

    # repos = ['facebook/react', 'facebook/react-native', 'facebook/react-native-web', 'facebook/react-native-scripts', 'facebook/react-native-renderer']
    repos = ['scottyab/rootbeer','Skyscanner/backpack','k9mail/k-9','mendhak/gpslogger']
    pull_info = []
    pull_request_data = pull_info
    pull_request_data = pull_info
    def get_pull_requests(self, repos):
        repos = ['scottyab/rootbeer','Skyscanner/backpack','k9mail/k-9','mendhak/gpslogger']
        pull_info = []
        pull_request_data = pull_info
        pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'
        """
        Get the pull requests from a repos
        """
        count = 0
        
        # 
        # 
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
        context = {
            pull_request_data: self.pull_request_data,
        }
                
        # context = {
        #     'mergerd_at' : len([pr['merged_at'] for pr in self.pull_info if pr['merged_at'] is not None]),
        #     'closed_at' : len([pr for pr in self.pull_info if pr['closed_at'] is not None and pr['merged_at'] is None]),
        #     'open_at' : len([pr for pr in self.pull_info if pr['closed_at'] is None]),
        # }
        
        return render(requests, "github/get_pull_requests.html", context)

    
        
        # for repo in repos:
        #     pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'
        #     pull_request_url = pull_request_url.format(repo)
        #     pull_request_data = requests.get(pull_request_url, auth=('goodman', 'sre2020-21'))
        #     pull_request_data = pull_request_data.json()
        #     for pull_request in pull_request_data:
        #         count += 1
        
        
        
        
from .get_all_pull_requests import get_droplets

# from get_pull_requests import get_pull_requests

# Create your views here.


from .get_all_pull_requests import get_droplets

class GetDroplets(TemplateView):
    template_name = 'droplets.html'
    def get_context_data(self, *args, **kwargs):
        context = {
            'droplets' : get_droplets(),
        }
        return context