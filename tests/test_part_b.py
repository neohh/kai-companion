"""
Часть B: тесты «живого Кая» — Mood, долги, ритуал, сезоны, фразы.
Правило B.4: рандом сидируется датой — всё воспроизводимо.
"""
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kai.core.relationship import Mood
from kai.core.contracts import DebtBook
from kai.core.rituals import EveningRitual
from kai.voice.seasons import SeasonWheel, SEASONS
from kai.core.phrases import DEFAULT_PHRASES, PhraseBank


def make_mood(tmp_path):
    return Mood(tmp_path / "progress.json")


def test_ignore_ladder_leads_to_boycott(tmp_path):
    m = make_mood(tmp_path)
    r1 = m.on_ignored()
    assert r1["strikes"] == 1 and not r1["boycott_started"]
    r2 = m.on_ignored()
    assert r2["strikes"] == 2 and not r2["boycott_started"]
    r3 = m.on_ignored()
    assert r3["boycott_started"] is True
    assert m.status() == "boycott"
    assert m.minutes_to_end() > 55  # ~60 мин


def test_boycott_reconciles_on_obeyed(tmp_path):
    m = make_mood(tmp_path)
    for _ in range(3):
        m.on_ignored()
    assert m.boycotting()
    assert m.on_obeyed() is True  # примирение
    assert not m.boycotting()
    assert m.status() in ("warm", "neutral", "cold")


def test_tasks_keep_working_during_boycott(tmp_path):
    """Правило B.2: бойкот не ломает функциональность."""
    m = make_mood(tmp_path)
    for _ in range(3):
        m.on_ignored()
    assert m.praise_allowed()  # экономика/XP продолжают работать
    assert m.pack() == "cold"


def test_debt_take_repay_pardon(tmp_path):
    d = DebtBook(tmp_path / "progress.json")
    assert d.minutes() == 0
    d.take_debt(5)
    d.take_debt(5)
    assert d.minutes() == 10
    assert "10 мин" in d.phrase()
    d.repay(7)
    assert d.minutes() == 3
    d.pardon(3)
    assert d.minutes() == 0
    assert d.phrase() == ""


def test_ritual_requires_answer(tmp_path):
    r = EveningRitual(tmp_path / "progress.json", hour=21, minute=0)
    from datetime import datetime
    evening = datetime(2026, 9, 15, 21, 30)
    assert r.due_now(evening)
    r.start(evening)
    assert r.pending()
    r.answer("Завтра сделаю репетицию задачи X")
    assert not r.pending()
    assert r.yesterday_obligation() == "Завтра сделаю репетицию задачи X"
    # второй раз в тот же день не срабатывает
    assert not r.due_now(evening)


def test_negotiation_due_by_ignore_rate(tmp_path):
    r = EveningRitual(tmp_path / "progress.json")
    for _ in range(6):
        r.count_ignored()
    assert r.ignore_rate_7d() == 1.0
    assert r.negotiation_due(0.5)
    r.mark_negotiated()
    assert not r.negotiation_due(0.5)  # раз в неделю


def test_season_rotation_weekly():
    w = SeasonWheel()
    d1 = date(2026, 9, 7)   # понедельник недели 1
    d2 = date(2026, 9, 14)  # +7 дней
    i1, i2 = w.index_for(d1), w.index_for(d2)
    assert i1 != i2
    assert w.current(d1)["name"] == SEASONS[i1]["name"]
    assert w.changes_today(d1)  # понедельник — день анонса
    assert not w.changes_today(date(2026, 9, 10))


def test_new_phrase_keys_exist():
    for key in ("debt_reminder", "praise_scarcity", "cold_pack", "warm_pack",
                "boycott_start", "boycott_end", "evening_ritual", "negotiation",
                "season_announce", "drop_common", "drop_rare", "drop_epic",
                "drop_legendary", "crit", "supercrit", "wheel_win",
                "wheel_nearmiss", "wheel_empty", "set_complete", "wager_win",
                "wager_lose", "double_drop_hour", "streak_at_risk"):
        assert key in DEFAULT_PHRASES, key


def test_old_phrase_data_still_loads(tmp_path):
    """Старый phrases.json без новых ключей читается, новые добираются из дефолта."""
    import json
    f = tmp_path / "phrases.json"
    f.write_text(json.dumps({"greet": ["Старое приветствие~"]}, ensure_ascii=False), encoding="utf-8")
    bank = PhraseBank(tmp_path)
    assert bank.get("greet") == "Старое приветствие~"
    assert bank.get("debt_reminder") in DEFAULT_PHRASES["debt_reminder"]
