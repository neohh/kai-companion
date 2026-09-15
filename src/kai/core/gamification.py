"""
core.gamification — XP, уровни, достижения, бои и ежедневные ивенты.
Владельцы: Gamification, BattleManager, DailyQuests.
Зависимости: json, pathlib, datetime; kai.constants (EQUIPMENT, ENEMIES, QUEST_DEFS).
Часть C: крит-ролл при выполнении задачи (10% x2, 1% x5), стрик-множитель
(x1.0 → x1.5 к 7 дню), стрик-фриз защищает стрик. Все множители — только
к наградам за реальную работу.
"""
import json
import random
from pathlib import Path
from datetime import date, timedelta

from kai.constants import EQUIPMENT, ENEMIES, QUEST_DEFS

CRIT_CHANCE = 0.10
SUPERCRIT_CHANCE = 0.01
STREAK_BONUS_MAX = 1.5
STREAK_BONUS_DAYS = 7


class Gamification:
    def __init__(self, data_dir):
        self.save_file = data_dir / "progress.json"
        self.data = self._load()

    def _load(self):
        if self.save_file.exists():
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"xp": 0, "level": 1, "tasks_done": 0, "rehearsals": 0,
                "achievements": [], "streak": 0, "last_done_date": None,
                "obey_count": 0}

    def _save(self):
        try:
            with open(self.save_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Save error:", e)

    def add_xp(self, amount):
        self.data["xp"] += amount
        new_level = int((self.data["xp"] / 100) ** 0.5) + 1
        leveled_up = new_level > self.data["level"]
        self.data["level"] = new_level
        self._save()
        return amount, leveled_up, new_level

    def next_level_xp(self):
        return self.data["level"] ** 2 * 100

    def level_start_xp(self):
        return (self.data["level"] - 1) ** 2 * 100

    def progress_percent(self):
        start, end = self.level_start_xp(), self.next_level_xp()
        if end == start:
            return 100
        return max(0, min(100, int(((self.data["xp"] - start) / (end - start)) * 100)))

    def unlock(self, key):
        if key not in self.data["achievements"]:
            self.data["achievements"].append(key)
            self._save()
            return True
        return False

    def add_obey(self):
        self.data["obey_count"] = self.data.get("obey_count", 0) + 1
        self._save()
        return self.data["obey_count"] >= 5

    def update_streak(self):
        today = date.today().isoformat()
        if self.data.get("last_done_date") == today:
            return False
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if self.data.get("last_done_date") == yesterday:
            self.data["streak"] = self.data.get("streak", 0) + 1
        elif self.data.get("streak_frozen_until") in (yesterday, today):
            # Часть C: стрик-фриз — пропуск дня не ломает стрик (отдых/сон)
            self.data["streak"] = self.data.get("streak", 0) + 1
            self.data["streak_frozen_until"] = None
        else:
            self.data["streak"] = 1
        self.data["last_done_date"] = today
        self._save()
        return self.data["streak"] >= 3

    def unlocked_equipment(self):
        return [name for lvl, name in EQUIPMENT if self.data["level"] >= lvl]

    def xp_multiplier(self):
        return 1.0 + 0.05 * len(self.unlocked_equipment())

    # --- Часть C: крит, стрик-множитель, стрик-фриз ---
    def roll_crit(self, seed=None):
        """(multiplier, kind): 1.0 normal | 2.0 crit | 5.0 supercrit."""
        rng = random.Random(seed) if seed is not None else random.random()
        roll = rng.random() if seed is not None else random.random()
        if roll < SUPERCRIT_CHANCE:
            return 5.0, "supercrit"
        if roll < SUPERCRIT_CHANCE + CRIT_CHANCE:
            return 2.0, "crit"
        return 1.0, "normal"

    def streak_multiplier(self):
        """x1.0 → x1.5 к 7 дню подряд (линейно)."""
        streak = self.data.get("streak", 0)
        if streak <= 0:
            return 1.0
        frac = min(streak, STREAK_BONUS_DAYS) / STREAK_BONUS_DAYS
        return 1.0 + (STREAK_BONUS_MAX - 1.0) * frac

    def use_streak_freeze(self):
        """Стрик-фриз: защита стрика при пропуске дня. Требует токен в wallet."""
        w = self.data.get("wallet", {}).get("tokens", {})
        if w.get("streak_freeze", 0) <= 0:
            return False
        w["streak_freeze"] -= 1
        self.data["streak_frozen_until"] = date.today().isoformat()
        self._save()
        return True

    def streak_frozen_today(self):
        return self.data.get("streak_frozen_until") == date.today().isoformat()


# ============================================
# БОИ
# ============================================
class BattleManager:
    def __init__(self, gamification):
        self.g = gamification
        d = self.g.data
        d.setdefault("enemy_index", 0)
        d.setdefault("enemy_hp", ENEMIES[0][2])
        d.setdefault("kills", 0)

    def current(self):
        i = self.g.data["enemy_index"] % len(ENEMIES)
        return ENEMIES[i]

    def hp(self):
        return self.g.data["enemy_hp"]

    def kills(self):
        return self.g.data["kills"]

    def damage(self, amount):
        d = self.g.data
        d["enemy_hp"] = max(0, d["enemy_hp"] - amount)
        defeated = d["enemy_hp"] == 0
        if defeated:
            d["kills"] += 1
            d["enemy_index"] += 1
            d["enemy_hp"] = self.current()[2]
        self.g._save()
        return defeated


# ============================================
# ЕЖЕДНЕВНЫЕ ИВЕНТЫ
# ============================================
class DailyQuests:
    def __init__(self, gamification):
        self.g = gamification
        d = self.g.data
        d.setdefault("quests_date", None)
        d.setdefault("quests", {})
        d.setdefault("quests_done", {})
        self.ensure_today()

    def ensure_today(self):
        today = date.today().isoformat()
        if self.g.data.get("quests_date") != today:
            self.g.data["quests_date"] = today
            self.g.data["quests"] = {k: 0 for k, _, _, _ in QUEST_DEFS}
            self.g.data["quests_done"] = {}
            self.g._save()

    def progress(self, key):
        self.ensure_today()
        d = self.g.data
        for k, desc, target, reward in QUEST_DEFS:
            if k == key:
                if d["quests_done"].get(k):
                    return 0
                d["quests"][k] = d["quests"].get(k, 0) + 1
                if d["quests"][k] >= target:
                    d["quests_done"][k] = True
                    self.g._save()
                    return reward
                self.g._save()
                return 0
        return 0

    def rows(self):
        self.ensure_today()
        out = []
        for k, desc, target, reward in QUEST_DEFS:
            prog = min(self.g.data["quests"].get(k, 0), target)
            done = self.g.data["quests_done"].get(k, False)
            out.append((done, desc, prog, target, reward))
        return out
