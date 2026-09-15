"""
core.loot — сундуки с добычей: вариативное подкрепление за реальную работу.
Владельцы: ChestEngine (сигнал drop_received).
Зависимости: random (сидируется датой — правило B.4/C), json, pathlib; PyQt6.
Редкости: common 60% / rare 25% / epic 12% / legendary 3%.
Pity: epic+ гарантирован каждые 10 сундуков; legendary — каждые 40.
Этические ограничители: вероятности открыты; pity-счётчики открыты;
при выключенном азарт-слое движок не используется (плоские награды).
"""
import json
import random
from pathlib import Path

from PyQt6.QtCore import pyqtSignal, QObject

RARITY_TABLE = [
    ("common", 60),
    ("rare", 25),
    ("epic", 12),
    ("legendary", 3),
]
PITY_EPIC = 10    # каждые 10 сундуков — epic+ гарантирован
PITY_LEGENDARY = 40  # каждые 40 — legendary гарантирован
DROP_CHANCE = 0.5  # базовый шанс сундука после задачи/репетиции

# содержимое по редкости: список фабрик (тип, параметр, вес)
LOOT_TABLE = {
    "common": [
        ("coins", 15, 50), ("coins", 25, 30), ("token", "reroll", 12),
        ("xp_mult", 1, 6), ("card", None, 2),
    ],
    "rare": [
        ("coins", 40, 40), ("coins", 60, 20), ("token", "streak_freeze", 15),
        ("token", "debt_pardon", 10), ("xp_mult", 1, 8), ("cosmetic", "рамка: аметист", 5),
        ("card", None, 2),
    ],
    "epic": [
        ("coins", 120, 35), ("token", "streak_freeze", 15), ("token", "debt_pardon", 10),
        ("xp_mult", 2, 20), ("cosmetic", "титул: Избранный фокуса", 10),
        ("cosmetic", "рамка: золотой дракон", 8), ("card", None, 2),
    ],
    "legendary": [
        ("coins", 300, 25), ("grace", "all_debt", 15), ("xp_mult", 5, 20),
        ("cosmetic", "титул: Легенда Кая", 20), ("cosmetic", "рамка: радужная аура", 15),
        ("card", None, 5),
    ],
}


class ChestEngine(QObject):
    drop_received = pyqtSignal(str, dict)  # (rarity, loot)

    def __init__(self, progress_file, seed=None):
        super().__init__()
        self.file = Path(progress_file)
        self.data = self._load()
        d = self.data
        d.setdefault("chests_opened", 0)
        d.setdefault("since_epic", 0)      # счётчик pity epic+
        d.setdefault("since_legendary", 0)  # счётчик pity legendary
        d.setdefault("inventory", [])       # история дропов (последние 100)
        d.setdefault("loot_enabled", True)  # этический выключатель слоя
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

    def set_enabled(self, on):
        self.data["loot_enabled"] = bool(on)
        self.save()

    def enabled(self):
        return bool(self.data.get("loot_enabled", True))

    # --- вероятности (открытые) ---
    def pity_info(self):
        return {"since_epic": self.data["since_epic"],
                "since_legendary": self.data["since_legendary"],
                "pity_epic": PITY_EPIC, "pity_legendary": PITY_LEGENDARY}

    @staticmethod
    def rarity_table():
        return list(RARITY_TABLE)

    def _roll_rarity(self):
        """Редкость с учётом pity; воспроизводимо при сиде."""
        rng = self._rng or random.Random()
        since_epic = self.data["since_epic"] + 1
        since_leg = self.data["since_legendary"] + 1
        if since_leg >= PITY_LEGENDARY:
            return "legendary"
        if since_epic >= PITY_EPIC:
            # epic или лучше: legendary идёт по своему pity, иначе epic
            return "epic"
        total = sum(w for _, w in RARITY_TABLE)
        roll = rng.randint(1, total)
        acc = 0
        for name, w in RARITY_TABLE:
            acc += w
            if roll <= acc:
                return name
        return "common"

    def open_chest(self, drop_chance=DROP_CHANCE):
        """Возвращает (rarity, loot)|None. None = сундука не выпало."""
        if not self.enabled():
            return None
        rng = self._rng or random.Random()
        if rng.random() >= drop_chance:
            return None
        rarity = self._roll_rarity()
        self.data["chests_opened"] += 1
        self.data["since_epic"] = 0 if rarity in ("epic", "legendary") else self.data["since_epic"] + 1
        self.data["since_legendary"] = 0 if rarity == "legendary" else self.data["since_legendary"] + 1
        loot = self._roll_loot(rarity)
        entry = {"rarity": rarity, **loot}
        self.data["inventory"] = ([entry] + self.data["inventory"])[:100]
        self.save()
        self.drop_received.emit(rarity, loot)
        return rarity, loot

    def _roll_loot(self, rarity):
        rng = self._rng or random.Random()
        table = LOOT_TABLE[rarity]
        total = sum(w for _, _, w in table)
        roll = rng.randint(1, total)
        acc = 0
        for kind, param, w in table:
            acc += w
            if roll <= acc:
                if kind == "coins":
                    return {"type": "coins", "amount": param}
                if kind == "token":
                    return {"type": "token", "token": param}
                if kind == "xp_mult":
                    return {"type": "xp_mult", "multiplier": param}
                if kind == "cosmetic":
                    return {"type": "cosmetic", "name": param}
                if kind == "grace":
                    return {"type": "grace", "name": param}
                if kind == "card":
                    return {"type": "card", "card_id": rng.randint(1, 12)}
        return {"type": "coins", "amount": 10}

    def reroll_last(self):
        """Реролл последнего сундука за токен/монеты — вернёт новый лут той же редкости."""
        if not self.data["inventory"]:
            return None
        last = self.data["inventory"][0]
        loot = self._roll_loot(last["rarity"])
        entry = {"rarity": last["rarity"], **loot, "rerolled": True}
        self.data["inventory"][0] = entry
        self.save()
        return last["rarity"], loot

    def history(self):
        return list(self.data["inventory"])
