import os
import sys
import json

# Add the repo root (one level above /tests) to PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.CollectFiles as cf
def test_countfiles_counts_files_across_commits(monkeypatch):
    """countfiles should count filenames returned by commit details."""

    # Fake commit list for page 1, then empty list to stop loop
    commit_pages = [
        [{"sha": "sha1"}, {"sha": "sha2"}],
        []
    ]

    # Fake details per sha
    sha_details = {
        "sha1": {"files": [{"filename": "a.txt"}, {"filename": "b.txt"}]},
        "sha2": {"files": [{"filename": "a.txt"}]},
    }

    calls = {"commit_page": 0}

    def fake_github_auth(url, tokens, ct):
        # If URL contains "/commits?page=", return commit page list
        if "commits?page=" in url:
            page_data = commit_pages[calls["commit_page"]]
            calls["commit_page"] += 1
            return page_data, ct
        # Otherwise it's a sha detail request
        sha = url.split("/commits/")[-1]
        return sha_details[sha], ct

    monkeypatch.setattr(cf, "github_auth", fake_github_auth)

    d = {}
    cf.countfiles(d, [], "owner/repo")

    assert d["a.txt"] == 2
    assert d["b.txt"] == 1


def test_countfiles_handles_missing_files_key(monkeypatch):
    """countfiles should not crash if sha details have no 'files' key."""

    commit_pages = [
        [{"sha": "sha1"}],
        []
    ]

    def fake_github_auth(url, tokens, ct):
        if "commits?page=" in url:
            # first page then stop
            return commit_pages.pop(0), ct
        # sha details missing 'files'
        return {}, ct

    monkeypatch.setattr(cf, "github_auth", fake_github_auth)

    d = {}
    cf.countfiles(d, [], "owner/repo")
    assert d == {}

def test_github_auth_handles_exception(monkeypatch, capsys):
    """github_auth should return (None, ct) and print error if requests fails."""

    def fake_get(url, headers=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(cf.requests, "get", fake_get)

    data, ct = cf.github_auth("http://example.com", ["t1"], 0)
    captured = capsys.readouterr()

    assert data is None
    # ct should remain 0 because it failed before increment
    assert ct == 0
    assert "boom" in captured.out


def test_main_writes_csv_without_network(monkeypatch, tmp_path):
    """main should write the output CSV when countfiles populates dictfiles."""

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)  # <-- ADD THIS

    def fake_countfiles(dictfiles, lsttokens, repo):
        dictfiles["a.txt"] = 2
        dictfiles["b.txt"] = 1

    monkeypatch.setattr(cf, "countfiles", fake_countfiles)

    cf.main()

    out_file = tmp_path / "data" / "file_rootbeer.csv"
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "Filename,Touches" in content
    assert "a.txt,2" in content
    assert "b.txt,1" in content


