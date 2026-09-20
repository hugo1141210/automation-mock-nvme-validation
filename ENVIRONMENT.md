# Development Environment

## Platform

- Operating System: Ubuntu 24.04.3 LTS
- Architecture: x86-64
- Virtualization: VMware
- Python: 3.12.3
- pip: 26.2.1

## Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
python -m pip install --upgrade pip==26.2.1
python -m pip install -r requirements.txt
```

## Verify Environment

```bash
python --version
python -m pip --version
pip freeze
```

Expected Python version:

```text
Python 3.12.3
```

Expected pip version:

```text
pip 26.2.1
```

## Notes

- The `.venv/` directory is local to each development environment and should not be committed to Git.
- Python package versions are defined in `requirements.txt`.
- This environment was recreated on VM-B to match the validated VM-A Python environment.

