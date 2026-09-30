#!/bin/zsh
# Körs automatiskt var 4:e timme av launchd (se scripts/com.adrianforsen.btclab.paper.plist).
# Bara papper: inga ordrar, ingen börsnyckel.
cd "$HOME/development/btc_lab" || exit 1
mkdir -p logs
{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  /opt/homebrew/bin/uv run python -m lab.paper --settle
  /opt/homebrew/bin/uv run python -m lab.paper
  /opt/homebrew/bin/uv run python -m lab.dashboard
} >> logs/paper_run.log 2>&1
