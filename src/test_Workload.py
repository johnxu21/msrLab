import json
import os

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
