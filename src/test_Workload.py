import json
import os

import pandas as pd

NOTEBOOK = os.path.join(os.path.dirname(__file__), 'Workload.ipynb')
PR_LIST_URL = 'https://api.github.com/repos/example/repo/pulls?page=1&per_page=100&state=closed'
ISSUE_LIST_URL = 'https://api.github.com/repos/example/repo/issues?page=1&per_page=100&state=all'


def code_cells():
    with open(NOTEBOOK, encoding='utf-8') as f:
        nb = json.load(f)
    return [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']


def cell_containing(text):
    matches = [c for c in code_cells() if text in c]
    assert len(matches) == 1, text
    return matches[0]


def run_workload(responses):
    # Run the notebook's own code cells with the GitHub fetch replaced by canned responses.
    # A URL missing from responses returns an empty list, which ends pagination.
    ns = {}
    exec(cell_containing('import pandas'), ns)
    exec(cell_containing('ignore_date = '), ns)
    exec(cell_containing('def login_of'), ns)
    ns['reponame'] = 'example/repo'
    ns['get_response'] = lambda url, token_list, ct: (responses.get(url, []), ct)
    exec(cell_containing('def pullrequest_details'), ns)
    exec(cell_containing('def issue_details'), ns)
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


def test_duplicate_first_names_stay_separate_for_pull_requests():
    prs = [merged_pr(1, 'alice-smith'), merged_pr(2, 'alice-jones')]

    ns = run_workload(pr_responses(prs))

    assert ns['contributor_pr_count'] == {'alice-smith': 1, 'alice-jones': 1}


def test_duplicate_first_names_stay_separate_for_issues_and_comments():
    responses = {
        ISSUE_LIST_URL: [issue(10, 'alice-jones')],
        'https://api.github.com/repos/example/repo/issues/10/comments': [{'user': user('alice-smith')}],
    }

    ns = run_workload(responses)

    assert ns['contributor_issue_count'] == {'alice-jones': 1}
    assert ns['contributor_comment_count'] == {'alice-smith': 1}


def test_participants_without_public_names_do_not_stop_processing():
    # Neither login has a public profile name in the mocked data, and the PR after the first is still counted
    prs = [merged_pr(1, 'no-name-user'), merged_pr(2, 'other-user')]

    ns = run_workload(pr_responses(prs))

    assert ns['contributor_pr_count'] == {'no-name-user': 1, 'other-user': 1}


def test_deleted_accounts_are_skipped_and_counted():
    # GitHub returns "user": null for deleted accounts; their activity has no login to credit
    prs = [merged_pr(1, None), merged_pr(2, 'bob')]
    reviews = {2: [{'user': None}, {'user': user('carol')}]}

    ns = run_workload(pr_responses(prs, reviews))

    assert ns['contributor_pr_count'] == {'bob': 1}
    assert ns['contributor_pr_review_count'] == {'carol': 1}
    assert ns['unattributed_count'] == 2


def test_self_review_is_excluded_by_value_not_identity():
    # Build equal logins at runtime so they are separate string objects
    author = ''.join(['car', 'ol'])
    same_login = ''.join(['ca', 'rol'])
    assert author == same_login and author is not same_login

    prs = [merged_pr(1, author)]
    reviews = {1: [{'user': user(same_login)}, {'user': user('dan')}]}

    ns = run_workload(pr_responses(prs, reviews))

    assert ns['contributor_pr_review_count'] == {'dan': 1}


def test_missing_pr_author_still_credits_identifiable_reviewers():
    # The PR's author was deleted, so its PR count and file metrics are skipped, but the reviewer is still credited
    prs = [merged_pr(1, None)]
    reviews = {1: [{'user': user('dan')}]}

    ns = run_workload(pr_responses(prs, reviews))

    assert ns['contributor_pr_count'] == {}
    assert ns['contributor_changedFiles_count'] == {}
    assert ns['contributor_pr_review_count'] == {'dan': 1}
    assert ns['unattributed_count'] == 1


def test_missing_issue_author_still_credits_identifiable_commenters():
    # The issue's author was deleted, so its issue count is skipped, but the commenter is still credited
    responses = {
        ISSUE_LIST_URL: [issue(10, None)],
        'https://api.github.com/repos/example/repo/issues/10/comments': [{'user': user('erin')}],
    }

    ns = run_workload(responses)

    assert ns['contributor_issue_count'] == {}
    assert ns['contributor_comment_count'] == {'erin': 1}
    assert ns['unattributed_count'] == 1


def run_dataframe_join(responses):
    # Run the DataFrame construction and the join, stopping before the plotting-selection filters (head and sort)
    ns = run_workload(responses)
    exec(cell_containing('df_pr = pd.DataFrame'), ns)
    join_code = cell_containing('df_list = [')
    before_filters, after_filters = join_code.split('df_merged = df_merged.fillna(0)')
    exec(before_filters, ns)
    return ns


def test_review_only_and_comment_only_participants_are_separate_rows_by_login():
    prs = [merged_pr(1, 'alice')]
    reviews = {1: [{'user': user('dan')}]}
    responses = pr_responses(prs, reviews)
    responses[ISSUE_LIST_URL] = [issue(10, 'alice')]
    responses['https://api.github.com/repos/example/repo/issues/10/comments'] = [{'user': user('erin')}]

    ns = run_dataframe_join(responses)
    df = ns['df_merged'].set_index('Login')

    assert sorted(df.index) == ['alice', 'dan', 'erin']
    assert df.loc['alice', 'PRs'] == 1 and df.loc['alice', 'Issues'] == 1
    # Review-only and comment-only rows have no count for the other activity; they are not merged into another row
    assert df.loc['dan', 'PR_Reviews'] == 1 and pd.isna(df.loc['dan', 'PRs'])
    assert df.loc['erin', 'Issue_Comments'] == 1 and pd.isna(df.loc['erin', 'PRs'])
