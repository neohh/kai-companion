"""
core.wheel — колесо фортуны: заряды за фокус-блоки и дейлики.
Владельцы: WheelFortune (сигнал spun).
Зависимости: random (сид даты), json, pathlib; PyQt6.
Сектора: монеты xN, XP, сундук, токен, благодать, пусто (~10%).
Near-miss: на «пусто» в ≤30% случаев флаг almost_jackpot; не чаще 1 раза в день
(этический ограничитель №5).
"""
import json
import random
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject

SECTORS = [
    {"id": "coins25", "label": "25 монет", "weight": 20, "loot": {"type": "coins", "amount": 25}},
    {"id": "coins75", "label": "75 монет", "weight": 12, "loot": {"type": "coins", "amount": 75}},
    {"id": "xp", "label": "XP-множитель", "weight": 12, "loot": {"type": "xp_mult", "multiplier": 2}},
    {"id": "chest", "label": "Сундук", "weight": 14, "loot": {"type": "chest"}},
    {"id": "token", "label": "Токен", "weight": 14, "loot": {"type": "token", "token": "reroll"}},
    {"id": "grace", "label": "Благодать Кая", "weight": 8, "loot": {"type": "grace", "name": "debt_15"}},
    {"id": "coins150", "label": "150 монет (джекпот)", "weight": 10,
     "loot": {"type": "coins", "amount": 150}},
    {"id": "empty", "label": "Пусто", "weight": 10, "loot": {"type": "empty"}},
]
NEAR_MISS_CHANCE = 0.30  # доля «пусто», которые оборачиваются дразнилкой


class WheelFortune(QObject):
    spun = pyqtSignal(dict)  # {"sector": id, "label": ..., "loot": {...}, "almost_jackpot": bool}

    def __init__(self, progress_file, seed=None):
        super().__init__()
        self.file = Path(progress_file)
        self.data = self._load()
        d = self.data
        d.setdefault("wheel_charges", 0)
        d.setdefault("wheel_spins_today", None)
        d.setdefault("wheel_spins_count", 0)
        d.setdefault("near_miss_last_date", None)
        d.setdefault("wheel_enabled", True)
        d.setdefault("wheel_daily_limit", 5)  # лимит спинов в день (настройка)
        self._rng = random.Random(seed)

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

    def _today(self):
        import datetime
        return datetime.date.today().isoformat()

    def set_enabled(self, on):
        self.data["wheel_enabled"] = bool(on)
        self.save()

    def enabled(self):
        return bool(self.data.get("wheel_enabled", True))

    # --- заряды ---
    def add_charge(self, source):
        """Фокус-блок и дейлик дают заряды."""
        if source in ("focus_block", "daily_quest"):
            self.data["wheel_charges"] += 1
            self.save()
            return self.data["wheel_charges"]
        return self.data["wheel_charges"]

    def charges(self):
        return self.data["wheel_charges"]

    def spins_left_today(self):
        used = self.data["wheel_spins_count"] if self.data.get("wheel_spins_today") == self._today() else 0
        return max(0, self.data.get("wheel_daily_limit", 5) - used)

    # --- спин ---
    def can_spin(self):
        return self.enabled() and self.charges() > 0 and self.spins_left_today() > 0

    def spin(self):
        if not self.can_spin():
            return None
        self.data["wheel_charges"] -= 1
        if self.data.get("wheel_spins_today") == self._today():
            self.data["wheel_spins_count"] += 1
        else:
            self.data["wheel_spins_today"] = self._today()
            self.data["wheel_spins_count"] = 1
        rng = self._rng or random.Random()
        total = sum(s["weight"] for s in SECTORS)
        roll = rng.randint(1, total)
        acc = 0
        sector = SECTORS[-1]
        for s in SECTORS:
            acc += s["weight"]
            if roll <= acc:
                sector = s
                break
        almost = False
        if sector["id"] == "empty" and rng.random() < NEAR_MISS_CHANCE:
            # ограничитель: near-miss не чаще 1 раза в день
            if self.data.get("near_miss_last_date") != self._today():
                almost = True
                self.data["near_miss_last_date"] = self._today()
        self.save()
        result = {"sector": sector["id"], "label": sector["label"],
                  "loot": sector["loot"], "almost_jackpot": almost}
        self.spun.emit(result)
        return result
