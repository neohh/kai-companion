"""
core.relationship — Mood: близость, настроение и реакция на игнор.
Владельцы: Mood.
Зависимости: json, random, time, pathlib; данные в progress.json (поля mood_*).
Правила B: у каждого негативного состояния есть путь исправления; тихий бойкот
не ломает функциональность — только внимание Кая; рандом сидируется датой.

Лестница игнора: 1 пропущенный выбор — мягко, 2 — твёрже,
3 — тихий бойкот (60 минут), после — примирение при следующем ответе.
"""
import random
import time
from pathlib import Path

IGNORE_LADDER = 3          # сколько игноров до бойкота
BOYCOTT_MINUTES = 60       # длительность тихого бойкота
DECAY_PER_DAY = 2          # естественное остывание близости в день
PRAISE_COOLDOWN = 40 * 60  # лимит похвалы: 1 раз / 40 мин (сек)


class Mood:
    """Близость 0..100, статус (warm/neutral/cold/boycott) и лестница игнора."""

    def __init__(self, progress_file):
        self.file = Path(progress_file)
        self.data = self._load()
        d = self.data
        d.setdefault("mood_closeness", 50)
        d.setdefault("mood_ignores", 0)
        d.setdefault("mood_boycott_until", 0)
        d.setdefault("mood_last_praise", 0)
        d.setdefault("mood_last_decay", None)
        d.setdefault("mood_ignore_threshold", IGNORE_LADDER)
        d.setdefault("mood_praise_cooldown_min", PRAISE_COOLDOWN // 60)
        self._rng = random.Random(self._today())

    # --- storage ---
    def _load(self):
        try:
            if self.file.exists():
                import json
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save(self):
        try:
            import json
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @staticmethod
    def _today():
        import datetime
        return datetime.date.today().isoformat()

    # --- state ---
    def closeness(self):
        return max(0, min(100, self.data["mood_closeness"]))

    def boycotting(self):
        return time.time() < self.data.get("mood_boycott_until", 0)

    def status(self):
        if self.boycotting():
            return "boycott"
        if self.closeness() >= 70:
            return "warm"
        if self.closeness() >= 35:
            return "neutral"
        return "cold"

    def status_emoji(self):
        return {"warm": "💜", "neutral": "😏", "cold": "🥶", "boycott": "silent"}

    def ignore_strikes(self):
        return self.data.get("mood_ignores", 0)

    def minutes_to_end(self):
        if not self.boycotting():
            return 0
        return int((self.data["mood_boycott_until"] - time.time()) // 60) + 1

    # --- events ---
    def on_obeyed(self):
        """Пользователь послушался/выбрал контакт: снятие бойкота = примирение."""
        reconciled = False
        if self.boycotting():
            self.data["mood_boycott_until"] = 0
            reconciled = True
        self.data["mood_ignores"] = 0
        self.data["mood_closeness"] = min(100, self.closeness() + 2)
        self.save()
        return reconciled

    def on_answered(self):
        self.data["mood_closeness"] = min(100, self.closeness() + 1)
        self.on_obeyed()

    def on_ignored(self):
        """Лестница игнора: 1 → мягко, 2 → твёрже, N (порог) → тихий бойкот."""
        self.data["mood_ignores"] = self.ignore_strikes() + 1
        self.data["mood_closeness"] = max(0, self.closeness() - 3)
        n = self.ignore_strikes()
        boycott_started = False
        if n >= self.threshold():
            self.data["mood_boycott_until"] = time.time() + BOYCOTT_MINUTES * 60
            boycott_started = True
            self.data["mood_ignores"] = 0
        self.save()
        return {"strikes": n, "boycott_started": boycott_started}

    def daily_decay(self):
        """Естественное остывание без контакта (вызывать раз в день)."""
        today = self._today()
        if self.data.get("mood_last_decay") == today:
            return
        self.data["mood_last_decay"] = today
        self.data["mood_closeness"] = max(0, self.closeness() - DECAY_PER_DAY)
        self.save()

    # --- praise scarcity ---
    def threshold(self):
        return int(self.data.get("mood_ignore_threshold", IGNORE_LADDER))

    def praise_cooldown_sec(self):
        return int(self.data.get("mood_praise_cooldown_min", PRAISE_COOLDOWN // 60)) * 60

    def praise_allowed(self):
        return time.time() - self.data.get("mood_last_praise", 0) >= self.praise_cooldown_sec()

    def mark_praise(self):
        self.data["mood_last_praise"] = time.time()
        self.save()

    # --- phrase packs ---
    def pack(self):
        """Пак фраз по статусу: warm/neutral/cold; бойкот = cold + молчание."""
        st = self.status()
        if st == "boycott":
            return "cold"
        if st == "warm":
            return "warm"
        return "neutral"

    # --- тесты: воспроизводимый рандом ---
    def _seeded(self):
        self._rng = random.Random(self._today())
        return self._rng
