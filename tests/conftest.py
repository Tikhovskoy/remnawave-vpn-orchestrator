"""Общие фикстуры для unit-тестов."""

import sys
from pathlib import Path

# Добавляем src в PYTHONPATH для корректного импорта
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
