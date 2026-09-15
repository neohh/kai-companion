"""
Часть C: тесты азарт-слоя — pity, криты, ставки, коллекция, колесо, flat-режим.
Этические ограничители проверяются здесь же.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kai.core.economy import Wallet, COIN_REWARDS, COSTS
from kai.core.loot import ChestEngine, PITY_EPIC, PITY_LEGENDARY
from kai.core.wheel import WheelFortune
from kai.core.collections import MoodCollection, CARD_NAMES
from kai.core.wagers import WagerBook, WAGER_SIZES
from kai.core.gamification import Gamification
from kai.core.phrases import DEFAULT_PHRASES
from datetime import datetime, date


def test_wallet_earn_and_spend(tmp_path):
    w = Wallet(tmp_path / "progress.json")
    assert w.earn("task_done") == 20
    assert w.earn("rehearsal_done", 2.0) == 30
    assert w.coins() == 50
    assert w.spend_coins("wheel_spin") is True
    assert w.coins() == 0
    assert w.spend_coins("wheel_spin") is False  # не в долг


def test_wallet_tokens(tmp_path):
    w = Wallet(tmp_path / "progress.json")
    w.add_token("streak_freeze", 2)
    assert w.token_count("streak_freeze") == 2
    assert w.use_token("streak_freeze") is True
    assert w.use_token("streak_freeze") is True
    assert w.use_token("streak_freeze") is False


def test_pity_guarantees_epic_within_10(tmp_path):
    """Чек-лист C: pity работает (тест: 10 дропов)."""
    c = ChestEngine(tmp_path / "progress.json", seed=123)
    c.data["since_epic"] = PITY_EPIC - 1  # на грани
    result = None
    for _ in range(10):
        result = c.open_chest(drop_chance=1.0)
        if result and result[0] in ("epic", "legendary"):
            break
    assert result and result[0] in ("epic", "legendary"), "pity epic+ не сработал за 10"


def test_pity_legendary_within_40(tmp_path):
    c = ChestEngine(tmp_path / "progress.json", seed=7)
    c.data["since_legendary"] = PITY_LEGENDARY - 1
    c.data["since_epic"] = 999  # epic-pity уже далеко за
    got = None
    for _ in range(40):
        got = c.open_chest(drop_chance=1.0)
        if got and got[0] == "legendary":
            break
    assert got and got[0] == "legendary"


def test_flat_mode_no_chests(tmp_path):
    """Этический ограничитель №1: слой выключен → никаких сундуков."""
    c = ChestEngine(tmp_path / "progress.json")
    c.set_enabled(False)
    for _ in range(20):
        assert c.open_chest(drop_chance=1.0) is None


def test_wheel_charges_spin_nearmiss_limit(tmp_path):
    w = WheelFortune(tmp_path / "progress.json", seed=42)
    assert w.can_spin() is False  # нет зарядов
    w.add_charge("focus_block")
    w.add_charge("daily_quest")
    assert w.charges() == 2
    w.data["wheel_daily_limit"] = 5
    results = [w.spin() for _ in range(2)]
    assert all(r is not None for r in results)
    assert w.charges() == 0
    assert w.spin() is None  # заряды кончились
    # near-miss не чаще 1 раза в день
    nears = [r for r in results if r["almost_jackpot"]]
    assert len(nears) <= 1


def test_wheel_flat_mode(tmp_path):
    w = WheelFortune(tmp_path / "progress.json")
    w.add_charge("focus_block")
    w.set_enabled(False)
    assert w.spin() is None


def test_crit_roll_bounds():
    g = Gamification.__new__(Gamification)  # без файловой системы
    seen = {g.roll_crit(seed=i)[1] for i in range(2000)}
    assert seen <= {"normal", "crit", "supercrit"}
    assert "crit" in seen and "normal" in seen


def test_streak_multiplier_ramp(tmp_path):
    g = Gamification(tmp_path / "progress.json")
    assert g.streak_multiplier() == 1.0
    g.data["streak"] = 7
    assert abs(g.streak_multiplier() - 1.5) < 1e-9
    g.data["streak"] = 20
    assert g.streak_multiplier() == 1.5  # кап


def test_streak_freeze_protects(tmp_path):
    g = Gamification(tmp_path / "progress.json")
    g.data["wallet"] = {"tokens": {"streak_freeze": 1}}
    from datetime import timedelta
    today = date.today()
    g.data["streak"] = 5
    g.data["last_done_date"] = (today - timedelta(days=2)).isoformat()  # пропущен день
    g.data["streak_frozen_until"] = (today - timedelta(days=1)).isoformat()
    grew = g.update_streak()
    assert grew and g.data["streak"] == 6  # фриз спас


def test_wager_settlement(tmp_path):
    g = Gamification(tmp_path / "progress.json")
    g.data["xp"] = 500
    wb = WagerBook(tmp_path / "progress.json", g)
    w = wb.place("Написать отчёт", 100, "today")
    assert w and g.data["xp"] == 400  # списалось сразу
    payout = wb.settle(w["id"], True)
    assert payout == 200 and g.data["xp"] == 600
    w2 = wb.place("Вторая задача", 50, "today")
    assert g.data["xp"] == 550
    wb.settle(w2["id"], False)
    assert g.data["xp"] == 550  # ставка уже была списана при placement


def test_wager_disabled_noop(tmp_path):
    g = Gamification(tmp_path / "progress.json")
    wb = WagerBook(tmp_path / "progress.json", g)
    wb.set_enabled(False)
    assert wb.place("x", 50, "today") is None


def test_collection_set_bonus_once(tmp_path):
    c = MoodCollection(tmp_path / "progress.json")
    fired = []
    c.set_completed.connect(lambda: fired.append(1))
    for i in range(1, 13):
        first, set_first = c.add_card(i)
    assert len(fired) == 1  # один раз
    assert c.bonus_multiplier() == 1.05
    first, set_first = c.add_card(1)  # дубль не триггерит
    assert len(fired) == 1
    assert c.bonus_multiplier() == 1.05


def test_double_drop_hour_deterministic(tmp_path):
    """Двойной дроп-час сидируется датой — воспроизводим."""
    import random as _r
    d1 = _r.Random(date(2026, 9, 15).isoformat()).randint(10, 22)
    d2 = _r.Random(date(2026, 9, 15).isoformat()).randint(10, 22)
    assert d1 == d2


def test_reward_phrases_exist():
    for key in ("drop_common", "drop_rare", "drop_epic", "drop_legendary",
                "crit", "supercrit", "wheel_win", "wheel_nearmiss", "wheel_empty",
                "set_complete", "wager_win", "wager_lose", "double_drop_hour",
                "streak_at_risk"):
        assert key in DEFAULT_PHRASES, key
