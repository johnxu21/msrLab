import csv
import json

import pytest

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
    def __init__(self, body):
        self.content = body


def test_github_auth_sends_token_and_returns_parsed_json(monkeypatch):
    seen = {}

    def fake_get(url, headers):
        seen['headers'] = headers
        return FakeResponse(json.dumps({'ok': True}).encode())

    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', 'test-token')
    monkeypatch.setattr(CollectFiles.requests, 'get', fake_get)

    result = CollectFiles.github_auth('https://api.github.com/some/url')

    assert result == {'ok': True}
    assert seen['headers']['Authorization'] == 'Bearer test-token'


def test_github_auth_returns_none_when_request_fails(monkeypatch):
    def failing_get(url, headers):
        raise ConnectionError('no network')

    monkeypatch.setattr(CollectFiles.requests, 'get', failing_get)

    assert CollectFiles.github_auth('https://api.github.com/some/url') is None


def test_countfiles_counts_each_file_once_per_commit(monkeypatch):
    monkeypatch.setattr(CollectFiles, 'github_auth', fake_github_auth)
    dictfiles = {}

    CollectFiles.countfiles(dictfiles, 'scottyab/rootbeer')

    assert dictfiles == {'x.java': 2, 'y.java': 1}


def test_countfiles_exits_with_status_1_on_bad_response(monkeypatch):
    # github_auth returns None on failure; len(None) then raises inside countfiles
    monkeypatch.setattr(CollectFiles, 'github_auth', lambda url: None)

    with pytest.raises(SystemExit) as exc:
        CollectFiles.countfiles({}, 'scottyab/rootbeer')

    assert exc.value.code == 1


def test_main_exits_without_creating_data_when_token_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CollectFiles, 'GITHUB_TOKEN', '')
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        CollectFiles.main()

    assert exc.value.code == 1
    assert 'GITHUB_TOKEN' in capsys.readouterr().err
    assert not (tmp_path / 'data').exists()


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
