"""
core.collections — коллекция «Настроения Кая»: 12 карт.
Владельцы: MoodCollection (сигнал card_obtained, set_completed).
Зависимости: json, pathlib; PyQt6. Дроп из репетиций и крит-задач.
Собранный сет → титул, рамка аватара, перманентно +5% XP (один раз).
"""
import json
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject

CARD_NAMES = [
    "Кай-смущёнка", "Кай-насмешник", "Кай-забота", "Кай-полночь",
    "Кай-дождь", "Кай-гроза", "Кай-утро", "Кай-кофе",
    "Кай-праздник", "Кай-тишина", "Кай-звёзды", "Кай-легенда",
]
SET_BONUS_XP = 0.05  # перманентно +5% XP


class MoodCollection(QObject):
    card_obtained = pyqtSignal(int)     # card_id 1..12
    set_completed = pyqtSignal()

    def __init__(self, progress_file):
        super().__init__()
        self.file = Path(progress_file)
        self.data = self._load()
        d = self.data
        d.setdefault("cards", {})           # id -> count
        d.setdefault("set_completed", False)

    def _load(self):
        try:
            if self.file.exists():
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save(self):
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def has_card(self, card_id):
        return card_id in self.data["cards"]

    def owned(self):
        return sorted(int(k) for k in self.data["cards"])

    def complete(self):
        return len(self.data["cards"]) >= len(CARD_NAMES)

    def add_card(self, card_id):
        """Вернёт (новая_карта?, сет_собран_впервые?)."""
        first_time = card_id not in self.data["cards"]
        if first_time:
            self.data["cards"][str(card_id)] = 1
        else:
            self.data["cards"][str(card_id)] += 1
        set_first = False
        if self.complete() and not self.data.get("set_completed"):
            self.data["set_completed"] = True
            set_first = True
            self.set_completed.emit()
        self.save()
        if first_time:
            self.card_obtained.emit(card_id)
        return first_time, set_first

    def bonus_multiplier(self):
        """Перманентный множитель XP от собранного сета."""
        return 1.0 + (SET_BONUS_XP if self.data.get("set_completed") else 0.0)
