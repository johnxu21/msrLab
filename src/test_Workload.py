import json
import os

import pandas as pd
import pytest
import requests

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import CollectFiles

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
NOTEBOOK = os.path.join(SRC_DIR, 'Workload.ipynb')
PR_LIST_URL = 'https://api.github.com/repos/example/repo/pulls?page=1&per_page=100&state=closed'
PR_LIST_PAGE_2 = 'https://api.github.com/repos/example/repo/pulls?page=2&per_page=100&state=closed'
ISSUE_LIST_URL = 'https://api.github.com/repos/example/repo/issues?page=1&per_page=100&state=all'
ISSUE_LIST_PAGE_2 = 'https://api.github.com/repos/example/repo/issues?page=2&per_page=100&state=all'
FILES_URL = 'https://api.github.com/repos/example/repo/pulls/1/files?per_page=100'
FILES_PAGE_2 = FILES_URL + '&page=2'
REVIEWS_URL = 'https://api.github.com/repos/example/repo/pulls/1/reviews?per_page=100'
REVIEWS_PAGE_2 = REVIEWS_URL + '&page=2'
COMMENTS_URL = 'https://api.github.com/repos/example/repo/issues/10/comments?per_page=100'
COMMENTS_PAGE_2 = COMMENTS_URL + '&page=2'


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


def fake_requests(monkeypatch, responses, requested):
    # Each URL maps to JSON data, a FakeResponse, or an exception to raise. Unlisted URLs get an empty list.
    # Every requested URL is appended to requested, in order.
    def fake_get(url, headers, timeout):
        requested.append(url)
        outcome = responses.get(url, [])
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, FakeResponse):
            return outcome
        return FakeResponse(body=json.dumps(outcome).encode())

    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)


def notebook_namespace(monkeypatch, responses, token='test-token', requested=None):
    # Run the notebook's setup cells in a fresh namespace, with requests.get faked
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', token)
    monkeypatch.chdir(SRC_DIR)
    fake_requests(monkeypatch, responses, [] if requested is None else requested)
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
    # Run the DataFrame construction and the join cell, which includes the ordering and the empty-table message
    exec(cell_containing('df_pr = pd.DataFrame'), ns)
    exec(cell_containing('df_list = ['), ns)


PLOT_CELL_MARKERS = ('y=["PRs", "PR_Reviews"', 'y=["Changed_Files"]', 'y=["Changed_LOC"]')


def run_plot_cell(ns, marker):
    # Runs one plotting cell and returns the axes it created, or None if the cell skipped the chart
    ns.pop('ax', None)
    exec(cell_containing(marker), ns)
    return ns.get('ax')


@pytest.fixture(autouse=True)
def no_plot_windows(monkeypatch):
    # Charts are drawn on the Agg backend, and figures are closed after each test
    monkeypatch.setattr(plt, 'show', lambda: None)
    yield
    plt.close('all')


def run_dataframe_join(monkeypatch, responses):
    ns = notebook_namespace(monkeypatch, responses)
    run_collection(ns)
    build_tables(ns)
    return ns


def user(login):
    return None if login is None else {'login': login}


def merged_pr(number, author, merged_at='2024-03-01T00:00:00Z'):
    return {'number': number, 'user': user(author), 'merged_at': merged_at}


def page(items, next_url=None):
    # One page of a list endpoint. next_url goes in the Link header, as GitHub sends it.
    links = {'next': {'url': next_url}} if next_url else {}
    return FakeResponse(body=json.dumps(items).encode(), links=links)


def files_entry(filename, changes=10):
    return {'filename': filename, 'changes': changes}


def pr_responses(prs, reviews=None):
    # Each PR changes one Java file. reviews maps a PR number to its review list.
    responses = {PR_LIST_URL: prs}
    for pr in prs:
        number = pr['number']
        responses['https://api.github.com/repos/example/repo/pulls/{}/files?per_page=100'.format(number)] = [
            {'filename': 'src/Main.java', 'changes': 10},
        ]
    for number, review_list in (reviews or {}).items():
        responses['https://api.github.com/repos/example/repo/pulls/{}/reviews?per_page=100'.format(number)] = review_list
    return responses


def issue(number, author, created_at='2024-03-01T00:00:00Z'):
    return {
        'number': number,
        'user': user(author),
        'created_at': created_at,
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
        COMMENTS_URL: [{'user': user('alice-smith')}],
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
        COMMENTS_URL: [{'user': user('erin')}],
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
    responses[COMMENTS_URL] = [{'user': user('erin')}]

    ns = run_dataframe_join(monkeypatch, responses)
    df = ns['df_merged'].set_index('Login')

    assert sorted(df.index) == ['alice', 'dan', 'erin']
    assert df.loc['alice', 'PRs'] == 1 and df.loc['alice', 'Issues'] == 1
    # Review-only and comment-only rows have a zero count for the other activity; they are not merged into another row
    assert df.loc['dan', 'PR_Reviews'] == 1 and df.loc['dan', 'PRs'] == 0
    assert df.loc['erin', 'Issue_Comments'] == 1 and df.loc['erin', 'PRs'] == 0


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
    fake_requests(monkeypatch, {}, [])

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

    fake_requests(monkeypatch, {PR_LIST_URL: FakeResponse(status_code=500)}, [])
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

    fake_requests(monkeypatch, {ISSUE_LIST_URL: FakeResponse(status_code=500)}, [])
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


def files_at_limit(start, count):
    return [files_entry('src/File{}.java'.format(i), changes=1) for i in range(start, start + count)]


def files_page_url(number):
    return FILES_URL if number == 1 else '{}&page={}'.format(FILES_URL, number)


def paged_files(total, final_next=None):
    # PR files in pages of at most 100 entries, each page at its own URL. Every page links to the next one,
    # and the last page links to final_next (None means no next link).
    starts = range(0, total, 100)
    responses = {}
    for number, start in enumerate(starts, start=1):
        count = min(100, total - start)
        next_url = files_page_url(number + 1) if start + count < total else final_next
        responses[files_page_url(number)] = page(files_at_limit(start, count), next_url)
    return responses


def files_request_sequence(pages):
    return [files_page_url(number) for number in range(1, pages + 1)]


def test_pr_files_on_a_later_page_are_counted(monkeypatch):
    # Page 1 holds only ignored extensions, so the counted file exists only on page 2
    first_page = [files_entry('docs/notes{}.json'.format(i)) for i in range(30)]
    responses = {
        PR_LIST_URL: [merged_pr(1, 'alice')],
        FILES_URL: page(first_page, FILES_PAGE_2),
        FILES_PAGE_2: page([files_entry('src/Main.java', changes=7)]),
    }
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    run_pr(ns)

    assert ns['contributor_changedFiles_count'] == {'alice': 1}
    assert ns['contributor_changedLOC'] == {'alice': 7}
    assert requested == [PR_LIST_URL, FILES_URL, FILES_PAGE_2, REVIEWS_URL, PR_LIST_PAGE_2]


def test_reviews_span_pages_and_each_reviewer_is_counted_once(monkeypatch):
    responses = pr_responses([merged_pr(1, 'alice')])
    responses[REVIEWS_URL] = page([{'user': user('dan')}, {'user': user('erin')}], REVIEWS_PAGE_2)
    responses[REVIEWS_PAGE_2] = page([
        {'user': user('dan')},
        {'user': user('alice')},
        {'user': user('frank')},
    ])
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    run_pr(ns)

    # dan reviewed on both pages, and alice's own review on page 2 is excluded
    assert ns['contributor_pr_review_count'] == {'dan': 1, 'erin': 1, 'frank': 1}
    assert requested == [PR_LIST_URL, FILES_URL, REVIEWS_URL, REVIEWS_PAGE_2, PR_LIST_PAGE_2]


def test_issue_comments_span_pages(monkeypatch):
    responses = {
        ISSUE_LIST_URL: [issue(10, 'alice')],
        COMMENTS_URL: page([{'user': user('erin')}], COMMENTS_PAGE_2),
        COMMENTS_PAGE_2: page([{'user': user('dan')}]),
    }
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    run_issues(ns)

    assert ns['contributor_comment_count'] == {'erin': 1, 'dan': 1}
    assert requested == [ISSUE_LIST_URL, COMMENTS_URL, COMMENTS_PAGE_2, ISSUE_LIST_PAGE_2]


def test_pr_files_below_the_cap_across_30_pages_are_complete(monkeypatch):
    # 2,999 entries in 30 pages of at most 100 each
    responses = {PR_LIST_URL: [merged_pr(1, 'alice')], **paged_files(2999)}
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    run_pr(ns)

    assert ns['contributor_changedFiles_count'] == {'alice': 2999}
    assert ns['contributor_changedLOC'] == {'alice': 2999}
    assert requested == [PR_LIST_URL] + files_request_sequence(30) + [REVIEWS_URL, PR_LIST_PAGE_2]


def test_pr_files_at_the_cap_on_the_final_page_without_a_next_link_raise(monkeypatch):
    # 3,000 entries in 30 pages, and the last page has no next link
    responses = {PR_LIST_URL: [merged_pr(1, 'alice')], **paged_files(3000)}
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    with pytest.raises(CollectFiles.GitHubError, match='cannot be established'):
        run_pr(ns)

    # Collection stops at page 30, which reaches the cap. Reviews are not requested.
    assert requested == [PR_LIST_URL] + files_request_sequence(30)
    assert 'contributor_pr_count' not in ns


def test_pr_files_at_the_cap_with_a_final_next_link_raise_without_fetching_it(monkeypatch):
    # 3,000 entries in 30 pages, and the last page links to a 31st page that must not be requested
    responses = {PR_LIST_URL: [merged_pr(1, 'alice')], **paged_files(3000, final_next=files_page_url(31))}
    responses[files_page_url(31)] = page([files_entry('src/Late.java')])
    requested = []
    ns = notebook_namespace(monkeypatch, responses, requested=requested)

    with pytest.raises(CollectFiles.GitHubError, match='cannot be established'):
        run_pr(ns)

    assert requested == [PR_LIST_URL] + files_request_sequence(30)
    assert 'contributor_pr_count' not in ns


def test_failure_on_a_later_files_page_after_progress_stores_nothing(monkeypatch):
    responses = {
        PR_LIST_URL: [merged_pr(1, 'alice')],
        FILES_URL: page([files_entry('src/Main.java')], FILES_PAGE_2),
        FILES_PAGE_2: FakeResponse(status_code=500),
    }
    ns = notebook_namespace(monkeypatch, responses)

    with pytest.raises(CollectFiles.GitHubError):
        run_pr(ns)

    assert 'contributor_pr_count' not in ns
    assert 'contributor_changedFiles_count' not in ns


def test_failed_pr_rerun_on_a_later_files_page_clears_dependent_tables(monkeypatch):
    # An earlier successful run, with PR files paged, builds every table
    responses = {
        PR_LIST_URL: [merged_pr(1, 'alice')],
        FILES_URL: page([files_entry('src/Main.java')], FILES_PAGE_2),
        FILES_PAGE_2: page([files_entry('src/Other.java')]),
        ISSUE_LIST_URL: [issue(10, 'erin')],
        COMMENTS_URL: [{'user': user('dan')}],
    }
    ns = run_dataframe_join(monkeypatch, responses)
    assert ns['df_merged'].shape[0] > 0

    # The PR-only rerun fails on page 2 of the files, after page 1 has been read
    fake_requests(monkeypatch, {
        PR_LIST_URL: [merged_pr(1, 'alice')],
        FILES_URL: page([files_entry('src/Main.java')], FILES_PAGE_2),
        FILES_PAGE_2: FakeResponse(status_code=500),
    }, [])
    with pytest.raises(CollectFiles.GitHubError):
        run_pr(ns)

    for name in ('contributor_pr_count', 'contributor_changedFiles_count', 'df_pr', 'df_pr_ChangedFiles', 'df_list', 'df_merged'):
        assert name not in ns
    # The issue step did not run, so its tables are still from the successful run
    assert ns['df_issues'].shape[0] == 1


def test_failed_issue_rerun_on_a_later_comment_page_clears_dependent_tables(monkeypatch):
    responses = {
        PR_LIST_URL: [merged_pr(1, 'alice')],
        ISSUE_LIST_URL: [issue(10, 'erin')],
        COMMENTS_URL: page([{'user': user('dan')}], COMMENTS_PAGE_2),
        COMMENTS_PAGE_2: page([{'user': user('frank')}]),
    }
    ns = run_dataframe_join(monkeypatch, responses)
    assert ns['df_issues_comments'].shape[0] == 2

    # The issue-only rerun fails on page 2 of the comments, after page 1 has been read
    fake_requests(monkeypatch, {
        ISSUE_LIST_URL: [issue(10, 'erin')],
        COMMENTS_URL: page([{'user': user('dan')}], COMMENTS_PAGE_2),
        COMMENTS_PAGE_2: FakeResponse(status_code=500),
    }, [])
    with pytest.raises(CollectFiles.GitHubError):
        run_issues(ns)

    for name in ('contributor_issue_count', 'contributor_comment_count', 'df_issues', 'df_issues_comments', 'df_list', 'df_merged'):
        assert name not in ns
    # The PR step did not run, so its tables are still from the successful run
    assert ns['df_pr'].shape[0] == 1


# The notebook's ignore_date is 2023-02-16T00:00:00 UTC. A timestamp counts only when it is strictly after it.
CUTOFF_CASES = [
    pytest.param('2023-02-15T23:59:59Z', False, id='one-second-before'),
    pytest.param('2023-02-16T00:00:00Z', False, id='exactly-at-cutoff'),
    pytest.param('2023-02-16T00:00:01Z', True, id='one-second-after'),
    pytest.param('2023-02-16T00:59:59Z', True, id='59-min-59-sec-after'),
    pytest.param('2023-02-16T01:00:00Z', True, id='one-hour-after'),
    pytest.param('2023-02-16T01:00:00+01:00', False, id='exact-cutoff-utc-plus-1'),
    pytest.param('2023-02-16T01:00:01+01:00', True, id='one-second-after-utc-plus-1'),
    pytest.param('2023-02-15T19:00:00-05:00', False, id='exact-cutoff-utc-minus-5'),
    pytest.param('2023-02-15T19:00:01-05:00', True, id='one-second-after-utc-minus-5'),
]


@pytest.mark.parametrize('merged_at, counted', CUTOFF_CASES)
def test_pull_request_counts_only_when_merged_after_the_cutoff(monkeypatch, merged_at, counted):
    ns = notebook_namespace(monkeypatch, pr_responses([merged_pr(1, 'alice', merged_at)]))

    run_pr(ns)

    expected = {'alice': 1} if counted else {}
    assert ns['contributor_pr_count'] == expected
    assert ns['contributor_changedFiles_count'] == expected


@pytest.mark.parametrize('created_at, counted', CUTOFF_CASES)
def test_issue_counts_only_when_created_after_the_cutoff(monkeypatch, created_at, counted):
    ns = notebook_namespace(monkeypatch, {ISSUE_LIST_URL: [issue(10, 'alice', created_at)]})

    run_issues(ns)

    assert ns['contributor_issue_count'] == ({'alice': 1} if counted else {})


def test_every_participant_appears_in_lowercase_login_order_with_review_and_comment_only_rows(monkeypatch):
    authors = ['Zed', 'alice', 'Bob', 'carol'] + ['user{:02d}'.format(i) for i in range(30)]
    prs = [merged_pr(number, login) for number, login in enumerate(authors, start=1)]
    responses = pr_responses(prs, {1: [{'user': user('reviewer_only')}]})
    responses[ISSUE_LIST_URL] = [issue(10, 'carol')]
    responses[COMMENTS_URL] = [{'user': user('commenter_only')}]
    ns = run_dataframe_join(monkeypatch, responses)

    expected = sorted(authors + ['reviewer_only', 'commenter_only'], key=lambda login: (login.lower(), login))
    df = ns['df_merged']
    assert df['Login'].tolist() == expected
    assert len(expected) == 36
    for column in ('PRs', 'PR_Reviews', 'Issues', 'Issue_Comments', 'Changed_Files', 'Changed_LOC'):
        assert pd.api.types.is_integer_dtype(df[column]), column


def test_participant_table_and_chart_bars_match_the_collected_counts(monkeypatch):
    authors = ['Zed', 'alice', 'Bob', 'carol'] + ['user{:02d}'.format(i) for i in range(30)]
    prs = [merged_pr(number, login) for number, login in enumerate(authors, start=1)]
    responses = pr_responses(prs, {1: [{'user': user('reviewer_only')}]})
    responses[ISSUE_LIST_URL] = [issue(10, 'carol')]
    responses[COMMENTS_URL] = [{'user': user('commenter_only')}]
    ns = run_dataframe_join(monkeypatch, responses)
    logins = ns['df_merged']['Login'].tolist()
    n = len(logins)

    # Every participant gets one bar per series, and each PR author's changed file has 10 lines
    contributions = run_plot_cell(ns, 'y=["PRs", "PR_Reviews"')
    assert [t.get_text() for t in contributions.get_xticklabels()] == logins
    assert contributions.get_xlabel() == 'GitHub login'
    assert contributions.get_ylabel() == 'Count (PRs, PR reviews, issues, issue comments)'
    assert contributions.get_legend_handles_labels()[1] == ['PRs', 'PR_Reviews', 'Issues', 'Issue_Comments']
    heights = [p.get_height() for p in contributions.patches]
    assert len(heights) == 4 * n
    # Pandas draws each series in turn, so each block of n bars matches one column of the table
    for index, column in enumerate(['PRs', 'PR_Reviews', 'Issues', 'Issue_Comments']):
        assert heights[index * n:(index + 1) * n] == ns['df_merged'][column].tolist(), column

    file_changes = run_plot_cell(ns, 'y=["Changed_Files"]')
    assert [t.get_text() for t in file_changes.get_xticklabels()] == logins
    assert file_changes.get_ylabel() == 'File changes across authored PRs'
    assert [p.get_height() for p in file_changes.patches] == [0 if login in ('reviewer_only', 'commenter_only') else 1 for login in logins]

    lines = run_plot_cell(ns, 'y=["Changed_LOC"]')
    assert [t.get_text() for t in lines.get_xticklabels()] == logins
    assert lines.get_ylabel() == 'Lines added + deleted across authored PRs'
    assert [p.get_height() for p in lines.patches] == [0 if login in ('reviewer_only', 'commenter_only') else 10 for login in logins]


def test_empty_results_print_one_message_and_every_plot_cell_skips(monkeypatch, capsys):
    ns = run_dataframe_join(monkeypatch, {})

    assert ns['df_merged'].empty
    assert capsys.readouterr().out.count('No participants were collected') == 1
    for marker in PLOT_CELL_MARKERS:
        assert run_plot_cell(ns, marker) is None
    assert plt.get_fignums() == []


def test_join_and_plots_after_a_failed_collection_raise_instead_of_showing_an_empty_table(monkeypatch):
    ns = run_dataframe_join(monkeypatch, pr_responses([merged_pr(1, 'alice')]))

    fake_requests(monkeypatch, {PR_LIST_URL: FakeResponse(status_code=500)}, [])
    with pytest.raises(CollectFiles.GitHubError):
        run_pr(ns)

    with pytest.raises(NameError):
        build_tables(ns)
    for marker in PLOT_CELL_MARKERS:
        with pytest.raises(NameError):
            run_plot_cell(ns, marker)
