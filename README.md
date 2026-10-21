# Lab on MSR
In this repo you will find the course content for lab Mining Repositories 

## Requirements

- Tested: Python 3.11 and Python 3.14, with the pinned packages.
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

## Running the notebook

From `src/`, with the environment active and `GITHUB_TOKEN` set:

```
jupyter notebook Workload.ipynb
```

The notebook asks for the kernel named `python3`, which the venv provides as "Python 3 (ipykernel)". Before running, check that the kernel uses the venv. In a new cell, which you can delete afterward, run:

```
import sys; print(sys.executable)
```

The path should contain `venvs/msrlab/bin/python`. If it does not, choose **Kernel > Change Kernel > Python 3 (ipykernel)** and run the check again.

Then choose **Run All**. The notebook calls the live GitHub API, so it needs network access and a valid token. Rerunning a single collection cell is covered in the notebook's markdown.
