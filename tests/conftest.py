"""Добавляет src/ в sys.path для запуска тестов без установки пакета."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
