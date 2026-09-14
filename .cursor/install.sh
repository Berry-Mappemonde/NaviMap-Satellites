#!/usr/bin/env bash
set -euo pipefail

# Ensure the Python venv tooling is present (default image ships python3.12
# without the venv/ensurepip module).
if ! python3 -c "import venv, ensurepip" >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv
fi

# Create the virtual environment once; reuse it on subsequent runs.
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
# Editable install with dev extras (pytest + netCDF4 reader).
.venv/bin/pip install -e ".[dev]"
