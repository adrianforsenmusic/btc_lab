import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Lokalt: logs/. Online (GitHub Actions) sätts BTCLAB_LOG_DIR=online/logs så loggarna hålls isär.
LOG_DIR = ROOT / os.environ.get("BTCLAB_LOG_DIR", "logs")
