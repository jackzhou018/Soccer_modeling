# Soccer

This repo has two kinds of Python state:

- [`requirements.txt`](/home/jack$/soccer/requirements.txt): the project dependency list you keep in git
- [`.venv/`](/home/jack$/soccer/.venv): a local throwaway environment created from that list

The important rule is: edit `requirements.txt`, not `.venv/`.

If `.venv/` gets messy, delete it and recreate it. That is normal workflow, not a mistake.

## Setup

Bootstrap the environment with:

```bash
./scripts/setup_venv.sh
```

That script will:

1. Create `.venv/` if needed
2. Install everything from `requirements.txt`
3. Register the Jupyter kernel inside the virtual environment

If you want to run the steps manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --sys-prefix --name soccer-venv --display-name "Python (.venv)"
```

## Package Management

Use this workflow:

- Add a package: put it in `requirements.txt`, then run `./scripts/setup_venv.sh`
- Update packages: adjust `requirements.txt`, then run `./scripts/setup_venv.sh`
- Rebuild from scratch: remove `.venv/`, then run `./scripts/setup_venv.sh`

Examples:

```bash
source .venv/bin/activate
python -m pip install pandas
python -m pip freeze
```

Do not treat `pip install ...` by itself as the final step. If you install something you want to keep, also add it to `requirements.txt`, otherwise it only exists in your current `.venv/`.

## Jupyter

Launch Jupyter from the virtual environment so it can see the environment's packages and kernels:

```bash
source .venv/bin/activate
python -m jupyter lab
```

You can also run:

```bash
./.venv/bin/jupyter lab
```

Select the kernel `Python (.venv)`. It points at [`.venv/bin/python`](/home/jack$/soccer/.venv/bin/python).

If you use VS Code, select the interpreter at [`.venv/bin/python`](/home/jack$/soccer/.venv/bin/python). If VS Code or Jupyter is launched outside the virtual environment, it may not see the repo kernel.
