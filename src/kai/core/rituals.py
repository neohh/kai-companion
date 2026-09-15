"""
core.rituals — вечерний ретроспектив и недельный детектор габитуации.
Владельцы: EveningRitual.
Зависимости: json, datetime, pathlib; состояние в progress.json (поля ritual_*).
Потоки: только QTimer снаружи (MainWindow); UI — только через сигналы владельца.
Правила B: ритуал требует обязательного ответа; детектор габитуации раз в неделю
считает долю игноров за 7 дней и предлагает «переговоры».
"""
import json
from pathlib import Path
from datetime import datetime, timedelta


class EveningRitual:
    def __init__(self, progress_file, hour=21, minute=0):
        self.file = Path(progress_file)
        self.data = self._load()
        d = self.data
        d.setdefault("ritual_hour", hour)
        d.setdefault("ritual_minute", minute)
        d.setdefault("ritual_last_date", None)
        d.setdefault("ritual_pending", False)
        d.setdefault("ritual_obligation", "")
        d.setdefault("negotiation_last", None)
        d.setdefault("daily_ignored", {})
        d.setdefault("daily_answered", {})

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

    # --- расписание ---
    def set_time(self, hour, minute):
        self.data["ritual_hour"] = hour
        self.data["ritual_minute"] = minute
        self.save()

    def due_now(self, now=None):
        now = now or datetime.now()
        today = now.date().isoformat()
        if self.data.get("ritual_last_date") == today:
            return False
        return (now.hour, now.minute) >= (self.data["ritual_hour"], self.data["ritual_minute"])

    def start(self, now=None):
        """Запустить ритуал: вопрос-обязательство, ответ обязателен."""
        now = now or datetime.now()
        self.data["ritual_last_date"] = now.date().isoformat()
        self.data["ritual_pending"] = True
        self.save()
        return True

    def pending(self):
        return bool(self.data.get("ritual_pending"))

    def answer(self, obligation_text):
        """Обязательный ответ получен: сохраняем обещание на завтра."""
        self.data["ritual_pending"] = False
        self.data["ritual_obligation"] = obligation_text.strip()
        self.save()

    def yesterday_obligation(self):
        return self.data.get("ritual_obligation", "")

    # --- учёт ответов/игноров (для детектора габитуации) ---
    def _bucket(self, key):
        today = datetime.now().date().isoformat()
        self.data.setdefault(key, {})
        self.data[key][today] = self.data[key].get(today, 0)
        return today

    def count_ignored(self, n=1):
        today = self._bucket("daily_ignored")
        self.data["daily_ignored"][today] += n
        self._prune()
        self.save()

    def count_answered(self, n=1):
        today = self._bucket("daily_answered")
        self.data["daily_answered"][today] += n
        self._prune()
        self.save()

    def _prune(self):
        cutoff = (datetime.now().date() - timedelta(days=7)).isoformat()
        for key in ("daily_ignored", "daily_answered"):
            self.data[key] = {d: v for d, v in self.data.get(key, {}).items() if d >= cutoff}

    def ignore_rate_7d(self):
        """Доля игноров за 7 дней: ignored / (ignored + answered)."""
        ig = sum(self.data.get("daily_ignored", {}).values())
        an = sum(self.data.get("daily_answered", {}).values())
        total = ig + an
        return (ig / total) if total else 0.0

    def negotiation_due(self, threshold=0.5):
        """Раз в неделю: если доля игнора за 7 дней выше порога — переговоры."""
        if not self.ignore_rate_7d() >= threshold:
            return False
        last = self.data.get("negotiation_last")
        if last:
            last = datetime.fromisoformat(last)
            if datetime.now() - last < timedelta(days=7):
                return False
        return True

    def mark_negotiated(self):
        self.data["negotiation_last"] = datetime.now().isoformat()
        self.save()
