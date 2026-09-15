"""
core.wagers — ставки XP на выполнение задачи с дедлайном.
Владельцы: WagerBook (сигналы wager_won, wager_lost).
Зависимости: json, datetime, pathlib; PyQt6. Реальных денег нет — только XP.
Активные ставки видны на странице задачи и в статус-баре.
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

from PyQt6.QtCore import pyqtSignal, QObject

WAGER_SIZES = [50, 100, 200]


class WagerBook(QObject):
    wager_won = pyqtSignal(int, int)   # (wager_id, выплата)
    wager_lost = pyqtSignal(int, int)  # (wager_id, потеряно)

    def __init__(self, progress_file, gamification=None):
        super().__init__()
        self.file = Path(progress_file)
        self.g = gamification
        self.data = self._load()
        d = self.data
        d.setdefault("wagers", [])
        d.setdefault("next_wager_id", 1)
        d.setdefault("wagers_enabled", True)

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

    def set_enabled(self, on):
        self.data["wagers_enabled"] = bool(on)
        self.save()

    def enabled(self):
        return bool(self.data.get("wagers_enabled", True))

    def active(self):
        return [w for w in self.data["wagers"] if w["status"] == "active"]

    def place(self, task_name, amount, deadline="today", now=None):
        """Ставка XP: amount из WAGER_SIZES; дедлайн сегодня/завтра."""
        if not self.enabled() or amount not in WAGER_SIZES:
            return None
        now = now or datetime.now()
        if deadline == "today":
            dl = now.replace(hour=23, minute=59, second=59)
        else:
            dl = (now + timedelta(days=1)).replace(hour=23, minute=59, second=59)
        # списываем XP сразу (риск реальный)
        if self.g is not None:
            self.g.data["xp"] = max(0, self.g.data["xp"] - amount)
            self.g._save()
        w = {"id": self.data["next_wager_id"], "task": task_name, "amount": amount,
             "deadline": dl.isoformat(), "status": "active",
             "placed_at": now.isoformat()}
        self.data["next_wager_id"] += 1
        self.data["wagers"].append(w)
        self.save()
        return w

    def settle(self, wager_id, task_completed, now=None):
        """Успел → x2 (возврат + выигрыш); нет → ставка уже списана."""
        now = now or datetime.now()
        for w in self.data["wagers"]:
            if w["id"] != wager_id or w["status"] != "active":
                continue
            if task_completed:
                w["status"] = "won"
                payout = w["amount"] * 2
                if self.g is not None:
                    self.g.data["xp"] += payout
                    self.g._save()
                self.save()
                self.wager_won.emit(wager_id, payout)
                return payout
            w["status"] = "lost"
            self.save()
            self.wager_lost.emit(wager_id, w["amount"])
            return 0
        return None

    def expire_overdue(self, now=None):
        """Просроченные активные ставки — проигрыш."""
        now = now or datetime.now()
        lost = []
        for w in self.data["wagers"]:
            if w["status"] == "active" and datetime.fromisoformat(w["deadline"]) < now:
                w["status"] = "lost"
                lost.append(w["id"])
                self.wager_lost.emit(w["id"], w["amount"])
        if lost:
            self.save()
        return lost
