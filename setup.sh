#!/usr/bin/env bash
# ============================================================
# setup.sh — Zorg Locaties Scraper — macOS setup
# Eénmalig uitvoeren: bash setup.sh
# ============================================================
set -e

echo ""
echo "=========================================="
echo " Zorg Locaties Scraper — Setup"
echo "=========================================="
echo ""

# ---- Python check ----
if ! command -v python3 &>/dev/null; then
  echo "Python 3 niet gevonden. Installeer via https://brew.sh of https://python.org"
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python versie: $PY_VERSION"

# Require Python 3.10+
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
  echo "Python 3.10+ vereist. Huidige versie: $PY_VERSION"
  echo "Installeer via: brew install python@3.11"
  exit 1
fi

# ---- Virtual environment ----
if [ ! -d ".venv" ]; then
  echo ""
  echo "Virtuele omgeving aanmaken..."
  python3 -m venv .venv
fi

echo "Virtuele omgeving activeren..."
source .venv/bin/activate

# ---- Dependencies ----
echo ""
echo "Paketten installeren..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ---- Directories ----
mkdir -p data/output

echo ""
echo "=========================================="
echo " Setup klaar!"
echo "=========================================="
echo ""
echo "Gebruik:"
echo ""
echo "  source .venv/bin/activate           # activeer de omgeving"
echo "  python main.py                       # alles draaien"
echo "  python main.py --scrapers search     # alleen DuckDuckGo zoeken"
echo "  python main.py --country NL          # alleen Nederland"
echo "  python main.py --small --emerging    # klein + opkomend"
echo "  python main.py --schedule            # elke 24 uur automatisch"
echo "  python main.py --help                # alle opties"
echo ""
