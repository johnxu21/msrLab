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
    'https://api.github.com/repos/scottyab/rootbeer/commits/a': {'files': [{'filename': 'x.java'}, {'filename': 'y.java'}]},
    'https://api.github.com/repos/scottyab/rootbeer/commits/b': {'files': [{'filename': 'x.java'}]},
}


def fake_github_auth(url):
    return FAKE_RESPONSES[url]


class FakeResponse:
    def __init__(self, body=b'[]', status_code=200, headers=None):
        self.content = body
        self.status_code = status_code
        self.headers = headers or {}


def fake_get_sequence(monkeypatch, outcomes):
    # Each call to requests.get returns the next outcome; an exception instance is raised instead
    calls = iter(outcomes)

    def fake_get(url, headers, timeout):
        outcome = next(calls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)


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
    monkeypatch.setattr(CollectFiles, 'github_auth', fake_github_auth)
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
    monkeypatch.setattr(CollectFiles, 'github_auth', fake_github_auth)
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
    # Commit list and first commit succeed; the second commit's details time out
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
    fake_get_sequence(monkeypatch, [FakeResponse(status_code=401)])

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert csv_path.read_text() == 'Filename,Touches\nold.java,9\n'
