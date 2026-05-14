#!/usr/bin/env bash
# ============================================================
# run_app.sh — Start de Zorg Locaties Finder webinterface
# Gebruik: bash run_app.sh
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activeer virtual environment
if [ ! -f ".venv/bin/activate" ]; then
  echo "Virtuele omgeving niet gevonden. Voer eerst uit: bash setup.sh"
  exit 1
fi
source .venv/bin/activate

echo ""
echo "=========================================="
echo " Zorg Locaties Finder — webinterface"
echo "=========================================="
echo ""
echo " Opent automatisch in je browser op:"
echo " http://localhost:8501"
echo ""
echo " Stop met Ctrl+C"
echo ""

streamlit run app.py \
  --server.headless false \
  --browser.gatherUsageStats false \
  --theme.primaryColor "#1F4E79" \
  --theme.backgroundColor "#ffffff" \
  --theme.secondaryBackgroundColor "#f0f6ff" \
  --theme.textColor "#1a1a1a"
