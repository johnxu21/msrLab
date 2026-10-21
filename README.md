# Lab on MSR
In this repo you will find the course content for lab Mining Repositories 

## Requirements

- Python 3.11: fully tested. The pinned packages install, all 41 tests pass, and the notebook, Jupyter launch, and kernel check were run.
- Python 3.14: installation and import verification only. The pinned packages install and import, but the test suite was not run on 3.14.
- Not tested: every other Python version. Python 3.9 cannot install the pinned packages.
- A GitHub personal access token. Creating one is covered below.

## Environment setup

Run these commands from the repository root. The virtual environment is created outside the repo so it is never committed. The commands use Python 3.11. To use 3.14 instead, replace `python3.11` with `python3.14`.

```
python3.11 -m venv ~/venvs/msrlab
source ~/venvs/msrlab/bin/activate
pip install -r requirements.txt
```

## GitHub token

The notebook reads the token from the `GITHUB_TOKEN` environment variable. It never accepts a token in a cell, and no file in this repo stores one. The tests do not need a token.

1. Create a token. The [GitHub documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-token) explains how. The link in `Workload.ipynb` pre-selects the `repo` scope.
2. Set it in the terminal you will start Jupyter from. The `read -s` form keeps the token out of your shell history:

```
read -s GITHUB_TOKEN && export GITHUB_TOKEN
```

If the variable is missing or blank, the notebook stops at its first collection cell and makes no request.

## Working directory

The notebook imports `CollectFiles` from its own folder, `src/`, so open it from there. Jupyter starts the notebook's kernel in the notebook's folder.

```
cd src
```

## Running the tests

The tests mock every GitHub request, so they need no network access. Run them from `src/`:

```
pytest -v
```

## Configure the notebook

Before Run All, open the configuration cell at the top of `Workload.ipynb` (the cell that sets `reponame` and `ignore_date`) and set:

- `reponame` to the repository you want to analyze, written as `owner/repository`, for example `"johnxu21/msrLab"`. The default is blank, so the first collection cell fails until you set it.
- `ignore_date` is the cutoff for collection. Pull requests are counted only if they were merged after this date, and issues only if they were created after it. Reviews and comments are not filtered by their own timestamps. They are counted for the pull requests and issues that pass the cutoff. The cutoff is the only timestamp filter in the notebook.

## Running the notebook

Start Jupyter from `src/`, with the environment active and `GITHUB_TOKEN` set:

```
jupyter notebook Workload.ipynb
```

The notebook's kernel is named `python3`. The venv provides it as "Python 3 (ipykernel)", but that label is not reliable on a machine that has other Python kernels. Register the venv under a unique name instead, once, with the venv active:

```
python -m ipykernel install --user --name msrlab-venv --display-name "msrLab (venv)"
```

In the notebook, choose **Kernel > Change Kernel > msrLab (venv)**. Then check which interpreter the kernel runs. In a new cell, which you can delete afterward, run:

```
import sys; print(sys.executable)
```

The path must contain `venvs/msrlab/bin/python`. If it does not, the kernel is wrong. Choose **msrLab (venv)** again, and check once more before continuing.

Changing the kernel does not change the notebook's cells or outputs. Saving the notebook may record the new kernel name in its metadata.

Then choose **Run All**. The notebook calls the live GitHub API, so it needs network access and a valid token. Rerunning a single collection cell is covered in the notebook's markdown.
