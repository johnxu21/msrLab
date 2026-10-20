import json
import os

import pandas as pd
import pytest
import requests

import CollectFiles

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(SRC_DIR, 'Workload.ipynb')
PR_LIST_URL = 'https://api.github.com/repos/example/repo/pulls?page=1&per_page=100&state=closed'
PR_LIST_PAGE_2 = 'https://api.github.com/repos/example/repo/pulls?page=2&per_page=100&state=closed'
ISSUE_LIST_URL = 'https://api.github.com/repos/example/repo/issues?page=1&per_page=100&state=all'


class FakeResponse:
    def __init__(self, body=b'[]', status_code=200, headers=None, links=None):
        self.content = body
        self.status_code = status_code
        self.headers = headers or {}
        self.links = links or {}


def code_cells():
    with open(NOTEBOOK, encoding='utf-8') as f:
        nb = json.load(f)
    return [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']


def cell_containing(text):
    matches = [c for c in code_cells() if text in c]
    assert len(matches) == 1, text
    return matches[0]


def fake_requests(monkeypatch, responses):
    # Each URL maps to JSON data, a FakeResponse, or an exception to raise. Unlisted URLs get an empty list.
    def fake_get(url, headers, timeout):
        outcome = responses.get(url, [])
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, FakeResponse):
            return outcome
        return FakeResponse(body=json.dumps(outcome).encode())

    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)


def notebook_namespace(monkeypatch, responses, token='test-token'):
    # Run the notebook's setup cells in a fresh namespace, with requests.get faked
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', token)
    monkeypatch.chdir(SRC_DIR)
    fake_requests(monkeypatch, responses)
    ns = {}
    exec(cell_containing('import pandas'), ns)
    exec(cell_containing('ignore_date = '), ns)
    ns['reponame'] = 'example/repo'
    exec(cell_containing('def fetch'), ns)
    exec(cell_containing('def invalidate'), ns)
    exec(cell_containing('def login_of'), ns)
    return ns


def run_pr(ns):
    exec(cell_containing('def pullrequest_details'), ns)


def run_issues(ns):
    exec(cell_containing('def issue_details'), ns)


def run_collection(ns):
    run_pr(ns)
    run_issues(ns)


def build_tables(ns):
    # Run the DataFrame construction and the join, stopping before the plotting-selection filters (head and sort)
    exec(cell_containing('df_pr = pd.DataFrame'), ns)
    join_code = cell_containing('df_list = [')
    before_filters, _ = join_code.split('df_merged = df_merged.fillna(0)')
    exec(before_filters, ns)


def run_dataframe_join(monkeypatch, responses):
    ns = notebook_namespace(monkeypatch, responses)
    run_collection(ns)
    build_tables(ns)
    return ns


def user(login):
    return None if login is None else {'login': login}


def merged_pr(number, author):
    return {'number': number, 'user': user(author), 'merged_at': '2024-03-01T00:00:00Z'}


def pr_responses(prs, reviews=None):
    # Each PR changes one Java file. reviews maps a PR number to its review list.
    responses = {PR_LIST_URL: prs}
    for pr in prs:
        number = pr['number']
        responses['https://api.github.com/repos/example/repo/pulls/{}/files'.format(number)] = [
            {'filename': 'src/Main.java', 'changes': 10},
        ]
    for number, review_list in (reviews or {}).items():
        responses['https://api.github.com/repos/example/repo/pulls/{}/reviews?per_page=100'.format(number)] = review_list
    return responses


def issue(number, author):
    return {
        'number': number,
        'user': user(author),
        'created_at': '2024-03-01T00:00:00Z',
        'comments_url': 'https://api.github.com/repos/example/repo/issues/{}/comments'.format(number),
    }


def test_duplicate_first_names_stay_separate_for_pull_requests(monkeypatch):
    prs = [merged_pr(1, 'alice-smith'), merged_pr(2, 'alice-jones')]
    ns = notebook_namespace(monkeypatch, pr_responses(prs))

    run_collection(ns)

    assert ns['contributor_pr_count'] == {'alice-smith': 1, 'alice-jones': 1}


def test_duplicate_first_names_stay_separate_for_issues_and_comments(monkeypatch):
    responses = {
        ISSUE_LIST_URL: [issue(10, 'alice-jones')],
        'https://api.github.com/repos/example/repo/issues/10/comments': [{'user': user('alice-smith')}],
    }
    ns = notebook_namespace(monkeypatch, responses)

    run_collection(ns)

    assert ns['contributor_issue_count'] == {'alice-jones': 1}
    assert ns['contributor_comment_count'] == {'alice-smith': 1}


def test_participants_without_public_names_do_not_stop_processing(monkeypatch):
    # Neither login has a public profile name in the mocked data, and the PR after the first is still counted
    prs = [merged_pr(1, 'no-name-user'), merged_pr(2, 'other-user')]
    ns = notebook_namespace(monkeypatch, pr_responses(prs))

    run_collection(ns)

    assert ns['contributor_pr_count'] == {'no-name-user': 1, 'other-user': 1}


def test_deleted_accounts_are_skipped_and_counted(monkeypatch):
    # GitHub returns "user": null for deleted accounts; their activity has no login to credit
    prs = [merged_pr(1, None), merged_pr(2, 'bob')]
    reviews = {2: [{'user': None}, {'user': user('carol')}]}
    ns = notebook_namespace(monkeypatch, pr_responses(prs, reviews))

    run_collection(ns)

    assert ns['contributor_pr_count'] == {'bob': 1}
    assert ns['contributor_pr_review_count'] == {'carol': 1}
    assert ns['unattributed'] == {'pr': 2, 'issues': 0}


def test_self_review_is_excluded_by_value_not_identity(monkeypatch):
    # Build equal logins at runtime so they are separate string objects
    author = ''.join(['car', 'ol'])
    same_login = ''.join(['ca', 'rol'])
    assert author == same_login and author is not same_login

    prs = [merged_pr(1, author)]
    reviews = {1: [{'user': user(same_login)}, {'user': user('dan')}]}
    ns = notebook_namespace(monkeypatch, pr_responses(prs, reviews))

    run_collection(ns)

    assert ns['contributor_pr_review_count'] == {'dan': 1}


def test_missing_pr_author_still_credits_identifiable_reviewers(monkeypatch):
    # The PR's author was deleted, so its PR count and file metrics are skipped, but the reviewer is still credited
    prs = [merged_pr(1, None)]
    reviews = {1: [{'user': user('dan')}]}
    ns = notebook_namespace(monkeypatch, pr_responses(prs, reviews))

    run_collection(ns)

    assert ns['contributor_pr_count'] == {}
    assert ns['contributor_changedFiles_count'] == {}
    assert ns['contributor_pr_review_count'] == {'dan': 1}
    assert ns['unattributed'] == {'pr': 1, 'issues': 0}


def test_missing_issue_author_still_credits_identifiable_commenters(monkeypatch):
    # The issue's author was deleted, so its issue count is skipped, but the commenter is still credited
    responses = {
        ISSUE_LIST_URL: [issue(10, None)],
        'https://api.github.com/repos/example/repo/issues/10/comments': [{'user': user('erin')}],
    }
    ns = notebook_namespace(monkeypatch, responses)

    run_collection(ns)

    assert ns['contributor_issue_count'] == {}
    assert ns['contributor_comment_count'] == {'erin': 1}
    assert ns['unattributed'] == {'pr': 0, 'issues': 1}


def test_review_only_and_comment_only_participants_are_separate_rows_by_login(monkeypatch):
    prs = [merged_pr(1, 'alice')]
    responses = pr_responses(prs, {1: [{'user': user('dan')}]})
    responses[ISSUE_LIST_URL] = [issue(10, 'alice')]
    responses['https://api.github.com/repos/example/repo/issues/10/comments'] = [{'user': user('erin')}]

    ns = run_dataframe_join(monkeypatch, responses)
    df = ns['df_merged'].set_index('Login')

    assert sorted(df.index) == ['alice', 'dan', 'erin']
    assert df.loc['alice', 'PRs'] == 1 and df.loc['alice', 'Issues'] == 1
    # Review-only and comment-only rows have no count for the other activity; they are not merged into another row
    assert df.loc['dan', 'PR_Reviews'] == 1 and pd.isna(df.loc['dan', 'PRs'])
    assert df.loc['erin', 'Issue_Comments'] == 1 and pd.isna(df.loc['erin', 'PRs'])


@pytest.mark.parametrize('failure', [
    FakeResponse(status_code=500),
    requests.Timeout('slow'),
    requests.ConnectionError('no network'),
    FakeResponse(body=b'<html>not json</html>'),
], ids=['http-500', 'timeout', 'connection', 'invalid-json'])
def test_request_failure_stops_collection_without_partial_results(monkeypatch, failure):
    ns = notebook_namespace(monkeypatch, {PR_LIST_URL: failure})

    with pytest.raises(CollectFiles.GitHubError):
        run_collection(ns)

    assert 'contributor_pr_count' not in ns
    assert 'contributor_issue_count' not in ns


def test_failure_on_a_later_page_stores_nothing(monkeypatch):
    responses = pr_responses([merged_pr(1, 'alice')])
    responses[PR_LIST_PAGE_2] = FakeResponse(status_code=500)
    ns = notebook_namespace(monkeypatch, responses)

    with pytest.raises(CollectFiles.GitHubError):
        run_collection(ns)

    assert 'contributor_pr_count' not in ns


@pytest.mark.parametrize('token', ['', '   '])
def test_missing_token_clears_populated_results_before_failing(monkeypatch, token):
    # Results from a successful run are present, then a rerun starts with a missing or blank token
    ns = run_dataframe_join(monkeypatch, pr_responses([merged_pr(1, 'alice')]))
    assert 'df_merged' in ns and 'contributor_pr_count' in ns

    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', token)
    fake_requests(monkeypatch, {})

    with pytest.raises(CollectFiles.GitHubError, match='GITHUB_TOKEN'):
        run_pr(ns)

    for name in ('contributor_pr_count', 'df_pr', 'df_list', 'df_merged'):
        assert name not in ns


def test_failed_pr_rerun_clears_pr_results_and_joined_table_only(monkeypatch):
    responses = pr_responses([merged_pr(1, 'alice')])
    responses[ISSUE_LIST_URL] = [issue(10, 'erin')]
    ns = notebook_namespace(monkeypatch, responses)
    run_collection(ns)
    build_tables(ns)

    fake_requests(monkeypatch, {PR_LIST_URL: FakeResponse(status_code=500)})
    with pytest.raises(CollectFiles.GitHubError):
        run_pr(ns)

    for name in ('contributor_pr_count', 'df_pr', 'df_list', 'df_merged'):
        assert name not in ns
    # The issue step did not run, so its own results are still the result of a successful run
    assert ns['df_issues'].shape[0] == 1


def test_failed_issue_rerun_clears_issue_results_and_joined_table_only(monkeypatch):
    responses = pr_responses([merged_pr(1, 'alice')])
    responses[ISSUE_LIST_URL] = [issue(10, 'erin')]
    ns = notebook_namespace(monkeypatch, responses)
    run_collection(ns)
    build_tables(ns)

    fake_requests(monkeypatch, {ISSUE_LIST_URL: FakeResponse(status_code=500)})
    with pytest.raises(CollectFiles.GitHubError):
        run_issues(ns)

    for name in ('contributor_issue_count', 'contributor_comment_count', 'df_issues', 'df_issues_comments', 'df_list', 'df_merged'):
        assert name not in ns
    # The PR step did not run, so its own results are still the result of a successful run
    assert ns['df_pr'].shape[0] == 1


def test_error_messages_never_show_the_token(monkeypatch, capsys):
    ns = notebook_namespace(monkeypatch, {PR_LIST_URL: FakeResponse(status_code=401)}, token='secret-token-value')

    with pytest.raises(CollectFiles.GitHubError) as exc:
        run_collection(ns)

    output = capsys.readouterr()
    assert 'secret-token-value' not in str(exc.value)
    assert 'secret-token-value' not in output.out + output.err
