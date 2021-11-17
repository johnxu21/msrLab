from django.contrib import admin
from django.urls import path, include

# CodeLogin_app/urls.py

from django.contrib import admin
from django.urls import path, include

from github.views import CollectFilesView, Get_Pull_Requests

urlpatterns = [
    # path('', CollectFilesView.as_view(), name='collect_files'),
    path('', Get_Pull_Requests.as_view(), name='get_pull_requests'),
]

# get_pull_requests/