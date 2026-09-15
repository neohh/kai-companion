"""
core.economy — кошелёк Кая: монеты и токены (reroll, streak_freeze, debt_pardon).
Владельцы: Wallet (сигнал economy_changed).
Зависимости: json, pathlib; PyQt6 (QObject, pyqtSignal); состояние в progress.json (поле wallet).
Часть C: начисления ТОЛЬКО за реальную работу; реальных денег нет.
"""
import json
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject

COIN_REWARDS = {
    "task_done": 20,
    "rehearsal_done": 15,
    "focus_block": 25,
    "daily_quest": 10,
    "obedience": 5,
}
COSTS = {
    "wheel_spin": 50,
    "chest_reroll": 30,
    "debt_pardon_minute": 20,
    "streak_freeze": 100,
}


class Wallet(QObject):
    economy_changed = pyqtSignal()

    def __init__(self, progress_file):
        super().__init__()
        self.file = Path(progress_file)
        self.data = self._load()
        w = self.data.setdefault("wallet", {})
        w.setdefault("coins", 0)
        w.setdefault("tokens", {"reroll": 0, "streak_freeze": 0, "debt_pardon": 0})
        w.setdefault("spent_total", 0)
        w.setdefault("earned_total", 0)

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

    # --- начисления за работу ---
    def earn(self, source, multiplier=1.0):
        amount = int(COIN_REWARDS.get(source, 0) * multiplier)
        if amount <= 0:
            return 0
        self.data["wallet"]["coins"] += amount
        self.data["wallet"]["earned_total"] += amount
        self.save()
        self.economy_changed.emit()
        return amount

    # --- покупки/расходы ---
    def spend_coins(self, cost_key):
        cost = COSTS.get(cost_key, 0)
        if self.data["wallet"]["coins"] < cost:
            return False
        self.data["wallet"]["coins"] -= cost
        self.data["wallet"]["spent_total"] += cost
        self.save()
        self.economy_changed.emit()
        return True

    def coins(self):
        return self.data["wallet"]["coins"]

    def add_token(self, token, n=1):
        self.data["wallet"]["tokens"][token] = self.data["wallet"]["tokens"].get(token, 0) + n
        self.save()
        self.economy_changed.emit()

    def use_token(self, token):
        t = self.data["wallet"]["tokens"]
        if t.get(token, 0) <= 0:
            return False
        t[token] -= 1
        self.save()
        self.economy_changed.emit()
        return True

    def token_count(self, token):
        return self.data["wallet"]["tokens"].get(token, 0)
