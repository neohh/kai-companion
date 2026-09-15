"""
core.contracts — долги и обещания («+5 мин в долг» из тоста-выбора).
Владельцы: DebtBook.
Зависимости: pathlib; данные в progress.json (поле debt_minutes).
Правила B: у долга есть явный путь погашения — фокус-блоки и прощение;
долг вплетается в речь плейсхолдером {debt}.
"""


class DebtBook:
    def __init__(self, progress_file):
        self.file = progress_file
        self.data = self._load()
        self.data.setdefault("debt_minutes", 0)

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

    def minutes(self):
        return self.data.get("debt_minutes", 0)

    def take_debt(self, minutes):
        self.data["debt_minutes"] = self.minutes() + int(minutes)
        self.save()
        return self.minutes()

    def repay(self, minutes):
        """Гашение долга фокус-блоком/работой."""
        self.data["debt_minutes"] = max(0, self.minutes() - int(minutes))
        self.save()
        return self.minutes()

    def pardon(self, minutes):
        """Прощение (токен/благодать Кая) — списание минут."""
        return self.repay(minutes)

    def breached(self):
        """Долг считается просроченным, если накопилось больше 30 минут."""
        return self.minutes() > 30

    def phrase(self):
        """Строка {debt} для вплетания в речь."""
        m = self.minutes()
        if m <= 0:
            return ""
        if m % 60 == 0:
            return f"долг: {m // 60} ч"
        if m < 60:
            return f"долг: {m} мин"
        return f"долг: {m // 60} ч {m % 60} мин"
