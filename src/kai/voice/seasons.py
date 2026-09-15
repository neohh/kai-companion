"""
voice.seasons — недельные сезонные стилевые примеси к манерам Gemini.
Владельцы: SeasonWheel.
Зависимости: datetime; ротация по дате (воспроизводимо, правило B.4).
Сезон меняется раз в 7 дней и анонсируется в greet (фраза season_announce).
"""
from datetime import date, timedelta

# Порядок ротации; тексты примесей добавляются к манере Gemini.
SEASONS = [
    {"key": "tenderness", "emoji": "🌸", "name": "Нежность",
     "style": "добавь в голос особенную нежность и мягкость"},
    {"key": "sarcasm", "emoji": "🌶", "name": "Сарказм",
     "style": "добавь в голос больше язвительной усмешки"},
    {"key": "strictness", "emoji": "🛡", "name": "Строгость",
     "style": "добавь в голос собранную строгость учителя"},
]
SEASON_WEEKS = 1  # каждый сезон держится 1 неделю


class SeasonWheel:
    def __init__(self, epoch=None):
        # epoch — фиксированная дата старта ротации (для тестов)
        self._epoch = epoch or date(2026, 1, 5)  # понедельник

    def index_for(self, day=None):
        d = day or date.today()
        weeks = (d - self._epoch).days // 7
        return weeks % len(SEASONS)

    def current(self, day=None):
        return SEASONS[self.index_for(day)]

    def changes_today(self, day=None):
        """Анонсировать смену сезона можно в первый день недели."""
        d = day or date.today()
        return (d - self._epoch).days % 7 == 0

    def next_name(self, day=None):
        d = day or date.today()
        nxt = (self.index_for(d) + 1) % len(SEASONS)
        delta = timedelta(days=(7 - (d - self._epoch).days % 7))
        return SEASONS[nxt]["name"], delta.days
