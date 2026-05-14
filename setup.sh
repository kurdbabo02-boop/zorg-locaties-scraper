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

# ---- Homebrew check ----
if ! command -v brew &>/dev/null; then
  echo "Homebrew niet gevonden. Installeer eerst via:"
  echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  exit 1
fi

# ---- Python 3.11 installeren indien nodig ----
PY311="$(brew --prefix)/bin/python3.11"

if [ ! -f "$PY311" ]; then
  echo "Python 3.11 niet gevonden. Wordt geïnstalleerd via Homebrew..."
  brew install python@3.11
else
  echo "Python 3.11 gevonden: $PY311"
fi

# Haal het exacte pad op (veilig na install)
PY311="$(brew --prefix python@3.11)/bin/python3.11"
if [ ! -f "$PY311" ]; then
  # fallback: zoek in Cellar
  PY311=$(find "$(brew --prefix)/Cellar/python@3.11" -name "python3.11" -type f 2>/dev/null | head -1)
fi

if [ -z "$PY311" ] || [ ! -f "$PY311" ]; then
  echo "Kon python3.11 niet vinden na installatie. Probeer: brew install python@3.11"
  exit 1
fi

echo "Gebruik Python: $PY311 (versie: $($PY311 --version))"

# ---- Virtual environment ----
if [ ! -d ".venv" ]; then
  echo ""
  echo "Virtuele omgeving aanmaken met Python 3.11..."
  "$PY311" -m venv .venv
else
  echo "Virtuele omgeving bestaat al (.venv)"
fi

# Activeer
source .venv/bin/activate

# ---- Dependencies ----
echo ""
echo "Paketten installeren..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# ---- Directories ----
mkdir -p data/output

# ---- run.sh aanmaken voor gemak ----
cat > run.sh << 'RUNSCRIPT'
#!/usr/bin/env bash
# Gebruik: bash run.sh [opties]
# Voorbeelden:
#   bash run.sh
#   bash run.sh --small --emerging
#   bash run.sh --country NL --export excel
#   bash run.sh --scrapers search
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
python "$SCRIPT_DIR/main.py" "$@"
RUNSCRIPT
chmod +x run.sh

echo ""
echo "=========================================="
echo " Setup klaar!"
echo "=========================================="
echo ""
echo "Draaien:"
echo ""
echo "  bash run.sh                        # alles draaien"
echo "  bash run.sh --small --emerging     # alleen klein + opkomend"
echo "  bash run.sh --country NL           # alleen Nederland"
echo "  bash run.sh --country BE           # alleen België"
echo "  bash run.sh --export excel         # exporteer naar Excel"
echo "  bash run.sh --schedule             # elke 24u automatisch"
echo "  bash run.sh --help                 # alle opties"
echo ""
echo "Of handmatig:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
