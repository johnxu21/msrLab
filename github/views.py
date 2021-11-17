from django.shortcuts import render
import requests
from .collectFiles import countFiles
from django.views.generic import TemplateView

from get_pull_requests import get_pull_requests

# Create your views here.

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
    
    pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'

    # repos = ['facebook/react', 'facebook/react-native', 'facebook/react-native-web', 'facebook/react-native-scripts', 'facebook/react-native-renderer']
    repos = ['scottyab/rootbeer','Skyscanner/backpack','k9mail/k-9','mendhak/gpslogger']
    pull_info = []
    pull_request_data = pull_info
    def get_pull_requests(self, repos):
        """
        Get the pull requests from a repos
        """
        count = 0
        
        for repo in repos:
            url = self.pull_request_url.format(repo)
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                for pr in data:
                    self.pull_info.append(pr)
                    count += 1
            else:
                print('Error: {}'.format(response.status_code))
                
        context = {
            'mergerd_at' : len([pr['merged_at'] for pr in self.pull_info if pr['merged_at'] is not None]),
            'closed_at' : len([pr for pr in self.pull_info if pr['closed_at'] is not None and pr['merged_at'] is None]),
            'open_at' : len([pr for pr in self.pull_info if pr['closed_at'] is None]),
        }
        
        return render(requests, "github/get_pull_requests.html", context)

        
        
        # for repo in repos:
        #     pull_request_url = 'https://api.github.com/repos/{}/pulls?state=all'
        #     pull_request_url = pull_request_url.format(repo)
        #     pull_request_data = requests.get(pull_request_url, auth=('goodman', 'sre2020-21'))
        #     pull_request_data = pull_request_data.json()
        #     for pull_request in pull_request_data:
        #         count += 1