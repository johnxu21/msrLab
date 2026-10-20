import csv
import importlib
import json

import pytest
import requests

import CollectFiles


# Fake responses for the GitHub URLs that countfiles requests.
# Page 1 has two commits, page 2 is empty, so the loop stops after page 2.
FAKE_RESPONSES = {
    'https://api.github.com/repos/scottyab/rootbeer/commits?page=1&per_page=100': [{'sha': 'a'}, {'sha': 'b'}],
    'https://api.github.com/repos/scottyab/rootbeer/commits?page=2&per_page=100': [],
    'https://api.github.com/repos/scottyab/rootbeer/commits/a?per_page=100': {'files': [{'filename': 'x.java'}, {'filename': 'y.java'}]},
    'https://api.github.com/repos/scottyab/rootbeer/commits/b?per_page=100': {'files': [{'filename': 'x.java'}]},
}

# Later files pages for commit a are requested through a next link
COMMIT_A_PAGE_2 = 'https://api.github.com/repos/scottyab/rootbeer/commits/a?page=2&per_page=100'


class FakeResponse:
    def __init__(self, body=b'[]', status_code=200, headers=None, links=None):
        self.content = body
        self.status_code = status_code
        self.headers = headers or {}
        self.links = links or {}


def files_page(names, next_url=None):
    # One page of a commit's changed files, with a next link when more pages exist
    body = json.dumps({'files': [{'filename': name} for name in names]}).encode()
    links = {'next': {'url': next_url}} if next_url else {}
    return FakeResponse(body=body, links=links)


def fake_get_routes(monkeypatch, routes):
    # Each URL returns its JSON body from routes
    def fake_get(url, headers, timeout):
        return FakeResponse(body=json.dumps(routes[url]).encode())

    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)


def fake_get_sequence(monkeypatch, outcomes):
    # Each call to requests.get returns the next outcome; an exception instance is raised instead
    calls = iter(outcomes)
    requested = []

    def fake_get(url, headers, timeout):
        requested.append(url)
        outcome = next(calls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)
    return requested


def test_github_auth_sends_token_with_timeout_and_returns_parsed_json(monkeypatch):
    seen = {}

    def fake_get(url, headers, timeout):
        seen['headers'] = headers
        seen['timeout'] = timeout
        return FakeResponse(json.dumps({'ok': True}).encode())

    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)

    assert CollectFiles.github_auth('https://api.github.com/some/url') == {'ok': True}
    assert seen['headers']['Authorization'] == 'Bearer test-token'
    assert seen['timeout'] == CollectFiles.REQUEST_TIMEOUT


def test_github_request_returns_next_link(monkeypatch):
    fake_get_sequence(monkeypatch, [
        FakeResponse(body=b'[]', links={'next': {'url': 'https://api.github.com/next'}}),
    ])

    data, next_url = CollectFiles.github_request('https://api.github.com/some/url')

    assert data == []
    assert next_url == 'https://api.github.com/next'


def test_github_auth_raises_on_http_401_without_leaking_token(monkeypatch):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    fake_get_sequence(monkeypatch, [FakeResponse(status_code=401)])

    with pytest.raises(CollectFiles.GitHubError) as exc:
        CollectFiles.github_auth('https://api.github.com/some/url')

    assert 'HTTP 401' in str(exc.value)
    assert 'GITHUB_TOKEN' in str(exc.value)
    assert 'test-token' not in str(exc.value)


def test_github_auth_raises_on_rate_limit(monkeypatch):
    headers = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1700000000'}
    fake_get_sequence(monkeypatch, [FakeResponse(status_code=403, headers=headers)])

    with pytest.raises(CollectFiles.GitHubError) as exc:
        CollectFiles.github_auth('https://api.github.com/some/url')

    assert 'rate limit' in str(exc.value)
    assert '1700000000' in str(exc.value)


def test_github_auth_raises_on_other_http_error(monkeypatch):
    fake_get_sequence(monkeypatch, [FakeResponse(status_code=500)])

    with pytest.raises(CollectFiles.GitHubError, match='HTTP 500'):
        CollectFiles.github_auth('https://api.github.com/some/url')


def test_github_auth_raises_on_timeout(monkeypatch):
    fake_get_sequence(monkeypatch, [requests.Timeout('slow')])

    with pytest.raises(CollectFiles.GitHubError, match='timed out'):
        CollectFiles.github_auth('https://api.github.com/some/url')


def test_github_auth_raises_on_connection_failure(monkeypatch):
    fake_get_sequence(monkeypatch, [requests.ConnectionError('no network')])

    with pytest.raises(CollectFiles.GitHubError, match='Could not connect'):
        CollectFiles.github_auth('https://api.github.com/some/url')


def test_github_auth_raises_on_invalid_json(monkeypatch):
    fake_get_sequence(monkeypatch, [FakeResponse(body=b'<html>not json</html>')])

    with pytest.raises(CollectFiles.GitHubError, match='invalid JSON'):
        CollectFiles.github_auth('https://api.github.com/some/url')


def test_countfiles_counts_each_file_once_per_commit(monkeypatch):
    fake_get_routes(monkeypatch, FAKE_RESPONSES)
    dictfiles = {}

    CollectFiles.countfiles(dictfiles, 'scottyab/rootbeer')

    assert dictfiles == {'x.java': 2, 'y.java': 1}


def test_countfiles_follows_next_links_across_file_pages(monkeypatch):
    requested = fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}]).encode()),
        files_page(['x.java', 'y.java'], next_url=COMMIT_A_PAGE_2),
        files_page(['z.java']),
        FakeResponse(body=b'[]'),
    ])
    dictfiles = {}

    CollectFiles.countfiles(dictfiles, 'scottyab/rootbeer')

    assert dictfiles == {'x.java': 1, 'y.java': 1, 'z.java': 1}
    assert requested[1] == 'https://api.github.com/repos/scottyab/rootbeer/commits/a?per_page=100'
    assert requested[2] == COMMIT_A_PAGE_2


def test_duplicate_paths_count_once_per_commit(monkeypatch):
    # x.java appears on both pages of commit a, and on commit b
    fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}, {'sha': 'b'}]).encode()),
        files_page(['x.java'], next_url=COMMIT_A_PAGE_2),
        files_page(['x.java', 'y.java']),
        files_page(['x.java']),
        FakeResponse(body=b'[]'),
    ])
    dictfiles = {}

    CollectFiles.countfiles(dictfiles, 'scottyab/rootbeer')

    assert dictfiles == {'x.java': 2, 'y.java': 1}


def test_countfiles_lets_github_error_propagate(monkeypatch):
    def failing_auth(url):
        raise CollectFiles.GitHubError('boom')

    monkeypatch.setattr(CollectFiles, 'github_auth', failing_auth)

    with pytest.raises(CollectFiles.GitHubError, match='boom'):
        CollectFiles.countfiles({}, 'scottyab/rootbeer')


def test_main_exits_without_creating_data_when_token_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', '')
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert 'GITHUB_TOKEN' in capsys.readouterr().err
    assert not (tmp_path / 'data').exists()


def test_blank_token_env_var_is_treated_as_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('GITHUB_TOKEN', '   ')
    importlib.reload(CollectFiles)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert 'GITHUB_TOKEN' in capsys.readouterr().err


def test_main_handles_repo_with_no_files(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.setattr(CollectFiles, 'github_auth', lambda url: [])
    monkeypatch.chdir(tmp_path)

    CollectFiles.main()

    with open(tmp_path / 'data' / 'file_rootbeer.csv', newline='') as f:
        rows = list(csv.reader(f))

    assert rows == [['Filename', 'Touches']]
    assert 'No files were found for scottyab/rootbeer' in capsys.readouterr().out


def test_main_writes_csv_with_counts(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    fake_get_routes(monkeypatch, FAKE_RESPONSES)
    monkeypatch.chdir(tmp_path)

    CollectFiles.main()

    with open(tmp_path / 'data' / 'file_rootbeer.csv', newline='') as f:
        rows = list(csv.reader(f))

    assert rows[0] == ['Filename', 'Touches']
    assert sorted(rows[1:]) == [['x.java', '2'], ['y.java', '1']]
    assert 'The file x.java has been touched 2 times.' in capsys.readouterr().out


def test_failure_after_earlier_success_exits_and_writes_no_csv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.chdir(tmp_path)
    # First commit page and its commit details succeed; the next commit-list page times out
    fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}]).encode()),
        FakeResponse(body=json.dumps({'files': [{'filename': 'x.java'}]}).encode()),
        requests.Timeout('slow'),
    ])

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert 'timed out' in capsys.readouterr().err
    assert not (tmp_path / 'data').exists()


def test_failure_does_not_overwrite_existing_csv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    csv_path = tmp_path / 'data' / 'file_rootbeer.csv'
    csv_path.write_text('Filename,Touches\nold.java,9\n')
    # First commit page and its details succeed, so real counts are collected before the 401 on page 2
    fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}]).encode()),
        FakeResponse(body=json.dumps({'files': [{'filename': 'x.java'}]}).encode()),
        FakeResponse(status_code=401),
    ])

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert csv_path.read_text() == 'Filename,Touches\nold.java,9\n'


def test_later_files_page_failure_preserves_existing_csv(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    csv_path = tmp_path / 'data' / 'file_rootbeer.csv'
    csv_path.write_text('Filename,Touches\nold.java,9\n')
    # Commit a's first files page succeeds and links to page 2, which returns a server error
    fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}]).encode()),
        files_page(['x.java'], next_url=COMMIT_A_PAGE_2),
        FakeResponse(status_code=500),
    ])

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert 'HTTP 500' in capsys.readouterr().err
    assert csv_path.read_text() == 'Filename,Touches\nold.java,9\n'


def commit_a_files_url(page):
    # The URL of commit a's files page; page 1 is the first request and has no page parameter
    if page == 1:
        return 'https://api.github.com/repos/scottyab/rootbeer/commits/a?per_page=100'
    return 'https://api.github.com/repos/scottyab/rootbeer/commits/a?page={}&per_page=100'.format(page)


@pytest.mark.parametrize('last_page_has_next_link', [True, False])
@pytest.mark.parametrize('names_repeat_across_pages', [False, True])
def test_reaching_file_cap_reports_uncertainty_and_preserves_csv(monkeypatch, tmp_path, capsys,
                                                                 last_page_has_next_link, names_repeat_across_pages):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'data').mkdir()
    csv_path = tmp_path / 'data' / 'file_rootbeer.csv'
    csv_path.write_text('Filename,Touches\nold.java,9\n')

    # 30 pages of 100 entries make 3000 entries. Each page links to the next one, except possibly the last.
    # With names_repeat_across_pages, every page lists the same 100 paths, so unique paths stay far below the cap.
    pages = []
    for page in range(1, 31):
        if names_repeat_across_pages:
            names = ['shared-{}.java'.format(i) for i in range(100)]
        else:
            names = ['f{}-{}.java'.format(page, i) for i in range(100)]
        is_last = page == 30
        next_url = None if is_last and not last_page_has_next_link else commit_a_files_url(page + 1)
        pages.append(files_page(names, next_url=next_url))
    requested = fake_get_sequence(monkeypatch, [
        FakeResponse(body=json.dumps([{'sha': 'a'}]).encode()),
        *pages,
    ])

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    # Requests follow the next links exactly, and the cap is checked after each page, so none is made past page 30
    expected_requests = [
        'https://api.github.com/repos/scottyab/rootbeer/commits?page=1&per_page=100',
        *[commit_a_files_url(page) for page in range(1, 31)],
    ]
    assert requested == expected_requests
    assert exc.value.code == 1
    assert 'cannot be established' in capsys.readouterr().err
    assert csv_path.read_text() == 'Filename,Touches\nold.java,9\n'
