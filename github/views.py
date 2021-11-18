from django.shortcuts import render
# from .collectFiles import countFiles
from django.views.generic import TemplateView
from .pull_requets import get_pull_requests
import requests

def get_context_data(self, **kwargs):
    
    context = {
        'pulls_data': get_pull_requests()
    }
    
    return context
