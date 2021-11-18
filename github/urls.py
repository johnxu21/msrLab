from django.contrib import admin
from django.urls import path, include

# CodeLogin_app/urls.py

from django.contrib import admin
from django.urls import path, include

from github.views import get_context_data

urlpatterns = [
    # path('', CollectFilesView.as_view(), name='collect_files'),
    # path('', , name='get_pull_requests'),
    path('', get_context_data, name='get_pull_requests'),
]

# get_pull_requests/