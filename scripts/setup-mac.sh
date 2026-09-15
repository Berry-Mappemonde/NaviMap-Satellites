#!/usr/bin/env bash
# Crée .venv et installe navimap-sat (Mac). À lancer depuis n'importe où :
#   bash scripts/setup-mac.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 introuvable. Installez Python 3.11+ (python.org) ou : brew install python" >&2
  exit 1
fi

if ! python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"; then
  echo "Python 3.11+ requis. Version actuelle : $(python3 --version)" >&2
  exit 1
fi

if ! python3 -c "import venv, ensurepip" >/dev/null 2>&1; then
  echo "Le module venv manque. Sur Mac : réinstallez Python 3.11+ depuis python.org" >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Création de .venv…"
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -e ".[dev]"

echo
echo "OK. Dans ce Terminal (le prompt doit montrer (.venv), pas seulement (base)) :"
echo "  source .venv/bin/activate"
echo "  navimap-sat --version"
echo
echo "Sans activer le venv :"
echo "  .venv/bin/navimap-sat --version"
