"""
Смоук-тесты: импорт всех модулей, clean_for_speech, PhraseBank.
Запуск: pytest tests/ (или python -m pytest tests/)
"""
import importlib

import kai
from kai.text_utils import clean_for_speech
from kai.core.phrases import PhraseBank, DEFAULT_PHRASES, EVENT_LABELS


def test_version():
    assert kai.__version__ == "1.0.0"


def test_import_all_modules():
    modules = [
        "kai.constants",
        "kai.text_utils",
        "kai.sys_utils",
        "kai.core.storage",
        "kai.core.gamification",
        "kai.core.phrases",
        "kai.core.monitor",
        "kai.core.avatar",
        "kai.core.companion",
        "kai.voice.styles",
        "kai.voice.gemini",
        "kai.voice.edge",
        "kai.voice.system_voice",
        "kai.voice.engine",
        "kai.ui.theme",
        "kai.ui.widgets",
        "kai.ui.dialogs",
        "kai.ui.nav",
        "kai.ui.status_bar",
        "kai.ui.main_window",
        "kai.ui.pages.projects",
        "kai.ui.pages.project",
        "kai.ui.pages.task",
        "kai.ui.pages.rehearsal",
        "kai.ui.pages.game",
        "kai.ui.pages.settings",
        "kai.__main__",
    ]
    for name in modules:
        importlib.import_module(name)


def test_clean_for_speech():
    assert clean_for_speech("Ммм, привет~ 💋") == "привет"
    assert clean_for_speech("М-м-м...  два   слова") == "два слова"
    assert clean_for_speech(",... Привет!") == "Привет!"


def test_phrase_bank(tmp_path):
    bank = PhraseBank(tmp_path)
    phrase = bank.say("greet")
    assert phrase and phrase != "..."
    assert bank.get("nonexistent_key") == "..."
    bank.data["greet"] = ["Тест~"]
    bank.save()
    bank2 = PhraseBank(tmp_path)
    assert bank2.get("greet") == "Тест~"
    bank2.reset()
    assert bank2.get("greet") in DEFAULT_PHRASES["greet"]


def test_event_labels_cover_phrases():
    keys = {k for k, _ in EVENT_LABELS}
    assert keys.issubset(set(DEFAULT_PHRASES.keys()))
