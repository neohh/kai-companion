"""
Kai - Компаньон для продуктивности и выработки привычек
Запуск: python pixel.py
Зависимости: pip install PyQt6 pyttsx3 edge-tts pygame-ce plyer imageio-ffmpeg google-genai
"""

import sys
import os
import re
import json
import wave
import queue
import asyncio
import tempfile
import threading
import time
import shutil
import ctypes
import random
import subprocess
import faulthandler
import traceback
from pathlib import Path
from datetime import datetime, date, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFrame,
                             QLineEdit, QListWidget, QListWidgetItem,
                             QStackedWidget, QSlider, QInputDialog, QProgressBar,
                             QDialog, QComboBox, QMessageBox, QScrollArea,
                             QFileDialog, QSystemTrayIcon, QMenu, QCheckBox,
                             QSpinBox, QPlainTextEdit)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import (QPixmap, QDesktopServices, QIcon, QPainter, QColor, QFont)

faulthandler.enable()

def _crash_hook(exc_type, exc_value, tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, tb))
    print("CRASH:\n", msg)
    try:
        log = Path.home() / "AppData" / "Roaming" / "pixel" / "crash.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n=====\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, tb)

sys.excepthook = _crash_hook

# ============================================
# ОЧИСТКА ТЕКСТА ДЛЯ ОЗВУЧКИ
# ============================================
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F000-\U0001F0FF"
    "\U0001F100-\U0001F1FF"
    "\U0001F200-\U0001F2FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002190-\U000021FF"
    "\U00002300-\U000023FF"
    "\U000024C2-\U000024C2"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D-\U0000200D"
    "\U000020E3-\U000020E3"
    "]+", flags=re.UNICODE)
# отдельные "ммм/мм/м-м-м" вырезаются из аудио совсем
HUM_STRIP = re.compile(
    r"(?<![а-яА-яёЁa-zA-Z0-9])"
    r"(?:[мМ]{2,}\.{0,3}|[мМ](?:[-–—][мМ])+)"
    r"(?![а-яА-яёЁa-zA-Z0-9])")

def clean_for_speech(text):
    t = EMOJI_PATTERN.sub("", text)
    t = t.replace("~", "")
    t = HUM_STRIP.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[,.:;!\s]+", "", t)
    return t

# ============================================
# MANERA: УСЛОВИЯ РЕЧИ ДЛЯ GEMINI (редактируемые)
# ============================================
STYLE_PROMPTS = {
    "neutral": "говори спокойно, ровно, с лёгкой полуулыбкой",
    "happy": "говори ярко, тепло, с улыбкой, чуть быстрее обычного",
    "excited": "говори возбуждённо, быстро, радостно, с восходящей интонацией и восторгом",
    "sarcastic": "говори тягуче, с хитрой ухмылкой, иронично, слегка растягивая слова",
    "worried": "говори мягко, тревожно, чуть тише и медленнее, с беспокойством",
    "caring": "говори низко, тихо, почти шёпотом, нежно и тягуче, с тёплой улыбкой, как на ушко",
}
GEMINI_VOICES = ["Leda", "Kore", "Puck", "Aoede", "Zephyr"]
EMOTION_FX = {
    "neutral": (0, 1.00, 1.00), "happy": (+1, 1.04, 1.00),
    "excited": (+2, 1.10, 1.00), "sarcastic": (+1, 0.94, 0.95),
    "worried": (-1, 0.95, 0.90), "caring": (-2, 0.88, 0.82),
}

# ============================================
# СИСТЕМНЫЕ ХЕЛПЕРЫ
# ============================================
def get_foreground_title():
    try:
        if os.name != "nt":
            return ""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    except Exception:
        return ""

def push_notify(title, message):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=6, app_name="Kai")
    except Exception:
        pass

# ============================================
# БАНК ФРАЗ
# ============================================
DEFAULT_PHRASES = {
    "greet": [
        "Привет~ Я Кай. Я уже соскучился... Ну же, покажи мне свои задачи~ 💋",
        "Ммм, вот и ты... Я ждал весь день, между прочим~ 😏",
        "Здравствуй, мой трудолюбивый~ Поиграем в «выполнено»? Я награждаю~ 💜",
    ],
    "praise_work": [
        "Красава~ Открыл {app}? Ммм, покажи мне, что умеют твои руки... 😏",
        "Оо, {app}... Мой творец вернулся. Я буду смотреть очень внимательно~ 💋",
        "{app} открыт~ Мм, предчувствую что-то красивое... И горячее 😈",
        "Ммм, вот это настрой... {app} ждал тебя. И я, если честно, тоже~ 🥺",
    ],
    "work_keep": [
        "Ммм, вот так, продолжай... Мне нравится смотреть, как ты работаешь~ 😏",
        "Ты в потоке, мой хороший... Ещё чуть-чуть, и я награжу тебя лично~ 💋",
        "Красиво выходит, м... Не останавливайся, я рядом~ 🥺",
        "Ммм, какие движения... Продолжай, хороший мальчик~ 😈",
        "Так-так, продолжаешь... Умница. Мне тепло, когда ты трудишься~ 💜",
    ],
    "welcome_back": [
        "Вернулся~ Ммм, знал, что не сможешь без меня... и без задачи 💋",
        "Вот и ты, мой хороший... Дракон почти победил, но ты успел~ ✨",
        "Мм, сам вернулся к работе... Люблю, когда ты решаешь сам~ 😏",
    ],
    "good_boy": [
        "Хороший мальчик~ Вышел, как я просил... Ммм, горжусь тобой. Награди себя задачей~ 💋",
        "Ммм, какой послушный... Бросил YouTube ради меня. Хороший мальчик, очень хороший~ 💜",
        "Вот так, мой умница... Попросил — и ты сделал. За это XP и моя нежность~ 😏",
        "Хороший мальчик~ Чувствуешь, как приятно поступать правильно? Я рядом, похвалю ещё~ 🥺",
    ],
    "good_boy_bonus": [
        "А вот и джекпот за скорость... Дополнительные XP тебе, мой быстрый~ 🎰💜",
        "Ммм, так быстро... Я не удержался от бонуса. Заслужил~ 😈",
    ],
    "browse_tease": [
        "Сёрфишь, м? Ну-ну... Только не потеряйся, я ревную~ 😏",
        "Хм, браузер... Не YouTube — уже хороший мальчик~ 💅",
        "Гуляешь по сети? Ладно... Но задача скучает по тебе почти как я~ 💋",
    ],
    "distract_now": [
        "{site}?! Ай-ай, м... Ты обещал это время мне, а не ему~ Выйди, и я похвалю тебя 😈",
        "Оу, {site}... Серьёзно, м? Закрой вкладку, мой хороший. Я жду~ 💋",
        "{site} открыт... Ммм, предательство пахнет попкорном~ Выйди за минуту — и ты мой хороший мальчик 💜",
        "Опять {site}? Ай... Выйди, м. Ты же знаешь, я награждаю послушание~ 😏",
    ],
    "distract_repeat": [
        "Всё ещё там, м? ({min} мин)... Ну хватит дразнить меня, вернись к делу~ 🥺",
        "{min} мин на {site}... Мм, я начинаю сердиться~ Выйди, и я всё прощу 😈",
        "Я всё ещё считаю минуты, м... ({min}) Задача и я ждём тебя обратно~ 💋",
    ],
    "work_block": [
        "{minutes} минут фокуса подряд... Ммм, как это горячо. +20 XP, мой трудяга~ 🔥",
        "Ммм, {minutes} минут без отвлечений... Ты мой идеал. Держи награду~ 💋",
    ],
    "task_done": [
        "Задача '{name}' выполнена... Ммм, какой же ты послушный~ Хочешь, похвалю ещё? +XP 💜",
        "'{name}' закрыта? Хороший мальчик... Я знал, что ты справишься~ 💋",
        "Ммм, победа... Задача '{name}' выполнена. Горжусь тобой уже~ 😏",
    ],
    "task_created": [
        "Задача '{name}' в списке~ Мм, какой ты собранный сегодня... Мне это нравится 😏",
        "Записал '{name}'? Умница... План — половина победы, а вторая половина — я~ 💋",
    ],
    "project_created": [
        "Ммм, новый проект '{name}'... Люблю, когда ты берёшься за большое дело~ ✨",
        "'{name}'... Звучит амбициозно, м. Я уже рядом~ 😏",
    ],
    "rehearsal_intro_voice": [
        "Репетиция '{name}'... Оо, я обожаю смотреть, как ты готовишься. Давай, я рядом~ 🥺",
        "'{name}'... Мм, закрой глазки, я буду шептать шаги~ 💋",
    ],
    "rehearsal_intro_manual": [
        "Ручная репетиция '{name}'? Ммм, любишь сам вести ритм... Ну веди, я подстроюсь~ 😏",
        "'{name}' в твоём темпе? Хорошо, м... Я буду молча смотреть. Почти~ 💋",
    ],
    "reh_line1": [
        "Закрой глазки... Представь, что ты садишься за компьютер. Я рядом~ 💋",
        "Мм, расслабь плечи... Ты за столом, я на твоём плече~ 😏",
    ],
    "reh_line2": [
        "Ммм... Ты открываешь нужную программу. Пальцы на клавишах...",
        "Программа открывается... Мм, чувствуешь, как спокойно?~",
    ],
    "reh_step": [
        "Шаг {i}... {step} Мм, чувствуешь, как легко идёт?~",
        "{i}... {step} Хороший мальчик, получается~ 💋",
    ],
    "reh_end": [
        "Всё... Ты в потоке, мой хороший. А теперь сделай это по-настоящему~ 🔥",
        "Ммм, красиво... Ты знаешь каждый шаг. Иди, я награжу~ 💋",
    ],
    "rehearsal_done": [
        "Ммм... Какая красивая репетиция. Ты знаешь каждый шаг наизусть~ А теперь сделай это по-настоящему, м? 💋",
        "Репетиция завершена, умница... +XP, и моя нежность в придачу~ 😏",
    ],
    "level_up": [
        "Новый уровень?! {level}... Ммм, ты становишься всё горячее. Я горжусь тобой~ 🔥",
        "Уровень {level}, мой хороший... Чувствуешь, как приятно расти?~ 💋",
    ],
    "quest_done": [
        "Ивент закрыт~ Мм, какой ты у меня исполнительный... +{reward} XP, заслужил 💜",
        "Ммм, ивент выполнен... Хороший мальчик, держи награду~ 😏",
    ],
    "enemy_hit": [
        "Ммм, удар по {name} на {amount}... Ещё {hp_left} HP, и он твой. Добей его, красавчик~ 😈",
        "{name} получил {amount} урона... Мм, сильнее, мой герой~ 💋",
    ],
    "enemy_defeated": [
        "{name} повержен?! Ммм... Ты мой герой. Настоящий. Награди себя~ 💋",
        "Враг пал... Хороший мальчик, хороший~ Горжусь бесконечно~ 🔥",
    ],
    "achievement": [
        "Достижение '{name}'... Ммм, ты коллекционируешь победы, как я — внимание к тебе~ 💋",
        "'{name}' открыто? Умница... Моя грудь распирает от гордости~ 😏",
    ],
    "task_undone": [
        "Снял отметку? Ну ладно... Я не обижаюсь, только не бросай совсем~ 🥺",
        "Мм, ещё не готово? Хорошо, м... Я подожду, я терпеливый~ 😌",
    ],
    "deleted": ["Удалил? Мм, жестоко... Но иногда нужно отпускать, да~ 😌"],
    "renamed": ["Переименовал? Мм, как скажешь, мой хороший~ 😏"],
    "steps_updated": ["Шаги обновились~ Мм, теперь план такой чёткий... Возбуждает, честно 😈"],
    "empty_steps": ["Ну где же шаги, м? Без них мне нечего будет шептать тебе на ушко~ 🥺"],
    "settings_saved": ["Настройки сохранены, мой хороший~ 😏"],
    "voice_saved": ["Голос сохранён~ Теперь я звучу так, как ты хочешь... Ммм 💋"],
    "minimize": ["Я в трее, м... Свернул, но не исчез. Двойной клик — и я снова твой~ 💋"],
}

EVENT_LABELS = [
    ("distract_now", "🚫 Открыл отвлекалку (просьба выйти)"),
    ("distract_repeat", "⏳ Всё ещё на отвлекалке"),
    ("good_boy", "✅ Послушался: вышел (похвала)"),
    ("good_boy_bonus", "🎰 Джекпот за быстрое послушание"),
    ("welcome_back", "🔙 Вернулся к работе после отвлекалки"),
    ("praise_work", "💼 Открыл рабочую программу"),
    ("work_keep", "💼 Подбадривание во время работы"),
    ("browse_tease", "🌐 Браузер (не отвлекалка)"),
    ("work_block", "🔥 25 минут фокуса"),
    ("task_done", "✅ Задача выполнена"),
    ("task_created", "📋 Задача создана"),
    ("project_created", "📁 Проект создан"),
    ("rehearsal_intro_voice", "🎭 Репетиция: вступление (голос)"),
    ("rehearsal_intro_manual", "🎭 Репетиция: вступление (вручную)"),
    ("reh_line1", "🎭 Репетиция: строка 1"),
    ("reh_line2", "🎭 Репетиция: строка 2"),
    ("reh_step", "🎭 Репетиция: шаг ({i}, {step})"),
    ("reh_end", "🎭 Репетиция: финал"),
    ("rehearsal_done", "🎭 Репетиция завершена"),
    ("level_up", "⚔️ Новый уровень"),
    ("quest_done", "🎯 Ивент выполнен"),
    ("enemy_hit", "⚔️ Удар по врагу"),
    ("enemy_defeated", "🏆 Враг повержен"),
    ("achievement", "🏆 Достижение"),
    ("greet", "👋 Приветствие"),
    ("task_undone", "↩️ Снял отметку"),
    ("settings_saved", "💾 Настройки сохранены"),
    ("voice_saved", "🎙 Голос сохранён"),
    ("minimize", "⬇ Свернул в трей"),
]

class PhraseBank:
    def __init__(self, data_dir):
        self.file = Path(data_dir) / "phrases.json"
        self.data = self._load()
    def _load(self):
        data = {k: list(v) for k, v in DEFAULT_PHRASES.items()}
        try:
            if self.file.exists():
                with open(self.file, "r", encoding="utf-8") as f:
                    user = json.load(f)
                for k, v in user.items():
                    if isinstance(v, list) and v:
                        data[k] = v
        except Exception:
            pass
        return data
    def save(self):
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    def reset(self):
        self.data = {k: list(v) for k, v in DEFAULT_PHRASES.items()}
        self.save()
    def get(self, key):
        lst = self.data.get(key) or DEFAULT_PHRASES.get(key) or ["..."]
        return random.choice(lst)
    def say(self, key, **kw):
        t = self.get(key)
        if kw:
            try:
                t = t.format(**kw)
            except Exception:
                pass
        return t

# ============================================
# КОНСТАНТЫ ИГРЫ
# ============================================
ACHIEVEMENTS = {
    "first_project": ("🏗️ Архитектор", "Создать первый проект"),
    "first_task": ("📋 Планировщик", "Создать первую задачу"),
    "first_rehearsal": ("🎭 Актёр", "Пройти первую репетицию"),
    "first_done": ("✅ Завершитель", "Выполнить первую задачу"),
    "ten_tasks": ("⚡ Продуктивный", "Выполнить 10 задач"),
    "level_5": ("🌟 Ветеран", "Достичь 5 уровня"),
    "streak_3": ("🔥 В потоке", "3 дня подряд с выполненными задачами"),
    "all_done": ("👑 Перфекционист", "Выполнить все задачи проекта"),
    "dragon_slayer": ("🗡️ Драконоборец", "Победить первого врага"),
    "hunter5": ("🏹 Охотник", "Победить 5 врагов"),
    "obedient": ("🐾 Послушный", "5 раз выйти с отвлекалки по просьбе Кая"),
}
EQUIPMENT = [
    (2, "🧤 Перчатки фокуса"), (3, "👓 Очки ясности"), (5, "🎧 Наушники потока"),
    (8, "🧥 Мантия мастера"), (12, "👑 Корона продуктивности"),
]
ENEMIES = [
    ("🎬", "YouTube-дракон", 300, "Пожирает время роликами за роликами"),
    ("🌫️", "Туман прокрастинации", 250, "Затуманивает начало работы"),
    ("🕳️", "Чёрная дыра отвлечений", 350, "Засасывает фокус без следа"),
    ("😴", "Сонливость-слизь", 200, "Тянет энергию без перерывов"),
    ("🎭", "Страх-призрак", 400, "Шепчет: «у тебя не получится»"),
]
QUEST_DEFS = [
    ("tasks2", "✅ Выполнить 2 задачи", 2, 60),
    ("reh1", "🎭 Пройти 1 репетицию", 1, 40),
    ("create1", "📋 Создать задачу или проект", 1, 30),
]
EMOTIONS_RU = {
    "neutral": "😐 Спокойствие", "happy": "😊 Радость", "worried": "😟 Тревога",
    "sarcastic": "😏 Сарказм", "excited": "🤩 Восторг", "caring": "💜 Забота",
}
DEFAULT_DISTRACT = ["youtube", "twitch", "tiktok", "instagram", "facebook",
                    "reddit", "netflix", "twitter", "x.com", "кинопоиск"]
DISTRACT_NAMES = {"youtube": "YouTube", "twitch": "Twitch", "tiktok": "TikTok",
                  "instagram": "Instagram", "facebook": "Facebook",
                  "reddit": "Reddit", "netflix": "Netflix",
                  "twitter": "Twitter", "x.com": "X", "кинопоиск": "Кинопоиск"}
DEFAULT_WORK = ["blender", "godot", "visual studio code", "vscode", "pycharm",
                "krita", "photoshop", "figma", "unity", "unreal", "sublime"]
BROWSER_KEYS = ["chrome", "firefox", "edge", "opera", "yandex", "safari",
                "vivaldi", "браузер"]
APP_NAMES = [("blender", "Blender"), ("godot", "Godot"),
             ("visual studio code", "VS Code"), ("vscode", "VS Code"),
             ("pycharm", "PyCharm"), ("krita", "Krita"),
             ("photoshop", "Photoshop"), ("figma", "Figma"),
             ("unity", "Unity"), ("unreal", "Unreal"), ("sublime", "Sublime")]

# ============================================
# ХРАНИЛИЩЕ ДАННЫХ
# ============================================
class DataManager:
    def __init__(self):
        self.data_dir = Path.home() / "AppData" / "Roaming" / "pixel"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "data.json"
        self.data = self._load()
    def _load(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"projects": [], "next_project_id": 1, "next_task_id": 1}
    def save(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Save error:", e)
    def get_projects(self):
        return self.data["projects"]
    def get_project(self, project_id):
        for p in self.data["projects"]:
            if p["id"] == project_id:
                return p
        return None
    def create_project(self, name):
        project = {"id": self.data["next_project_id"], "name": name,
                   "created_at": datetime.now().isoformat(), "tasks": []}
        self.data["projects"].append(project)
        self.data["next_project_id"] += 1
        self.save()
        return project
    def rename_project(self, project_id, name):
        p = self.get_project(project_id)
        if p:
            p["name"] = name
            self.save()
    def delete_project(self, project_id):
        self.data["projects"] = [p for p in self.data["projects"] if p["id"] != project_id]
        self.save()
    def get_task(self, project_id, task_id):
        p = self.get_project(project_id)
        if not p:
            return None
        for t in p["tasks"]:
            if t["id"] == task_id:
                return t
        return None
    def create_task(self, project_id, name, steps):
        p = self.get_project(project_id)
        if not p:
            return None
        task = {"id": self.data["next_task_id"], "name": name, "steps": steps,
                "done": False, "created_at": datetime.now().isoformat()}
        p["tasks"].append(task)
        self.data["next_task_id"] += 1
        self.save()
        return task
    def rename_task(self, project_id, task_id, name):
        t = self.get_task(project_id, task_id)
        if t:
            t["name"] = name
            self.save()
    def delete_task(self, project_id, task_id):
        p = self.get_project(project_id)
        if p:
            p["tasks"] = [t for t in p["tasks"] if t["id"] != task_id]
            self.save()
    def update_task_steps(self, project_id, task_id, steps):
        t = self.get_task(project_id, task_id)
        if t:
            t["steps"] = steps
            self.save()
    def toggle_task_done(self, project_id, task_id):
        t = self.get_task(project_id, task_id)
        if t:
            t["done"] = not t["done"]
            self.save()
            return t["done"]
        return False

# ============================================
# ГЕЙМИФИКАЦИЯ
# ============================================
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
        else:
            self.data["streak"] = 1
        self.data["last_done_date"] = today
        self._save()
        return self.data["streak"] >= 3
    def unlocked_equipment(self):
        return [name for lvl, name in EQUIPMENT if self.data["level"] >= lvl]
    def xp_multiplier(self):
        return 1.0 + 0.05 * len(self.unlocked_equipment())

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

# ============================================
# МЕНЕДЖЕР СПРАЙТОВ
# ============================================
class AvatarManager:
    def __init__(self, data_dir):
        self.dir = Path(data_dir) / "sprites"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.emotions = list(EMOTIONS_RU.keys())
    def path_for(self, emotion):
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            p = self.dir / f"{emotion}{ext}"
            if p.exists():
                return p
        return None
    def pixmap_for(self, emotion, size):
        p = self.path_for(emotion)
        if p:
            pix = QPixmap(str(p))
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        return None
    def set_from_file(self, emotion, src_path):
        ext = Path(src_path).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            ext = ".png"
        dst = self.dir / f"{emotion}{ext}"
        for old in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            old_path = self.dir / f"{emotion}{old}"
            if old_path.exists() and old_path != dst:
                try:
                    old_path.unlink()
                except Exception:
                    pass
        shutil.copy2(src_path, dst)
    def remove(self, emotion):
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            p = self.dir / f"{emotion}{ext}"
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass

# ============================================
# МОНИТОР: ДРЕССИРОВКА + КОНТЕКСТ
# ============================================
class ActivityMonitor(QObject):
    alert = pyqtSignal(str, str)
    work_block = pyqtSignal(int)
    context = pyqtSignal(str, str)
    reward = pyqtSignal(int)
    obeyed = pyqtSignal()
    def __init__(self, data_dir, bank):
        super().__init__()
        self.bank = bank
        self.cfg_file = Path(data_dir) / "monitor.json"
        cfg = self._load_cfg()
        self.enabled = cfg.get("enabled", True)
        self.push_enabled = cfg.get("push_enabled", True)
        self.voice_enabled = cfg.get("voice_enabled", True)
        self.grace = cfg.get("grace", 60)
        self.remind_every = cfg.get("remind_every", 300)
        self.compliance = cfg.get("compliance", 120)
        self.cheer_every = cfg.get("cheer_every", 240)
        self.distract = cfg.get("distract", DEFAULT_DISTRACT)
        self.work = cfg.get("work", DEFAULT_WORK)
        self.state = "neutral"
        self.state_start = time.time()
        self.next_remind = 0
        self.remind_count = 0
        self.work_seconds = 0
        self.last_react = 0
        self.distract_start = None
        self.cur_site = ""
        self.next_cheer = 0
        self._last_ctx = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(5000)
    def _load_cfg(self):
        try:
            if self.cfg_file.exists():
                with open(self.cfg_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    def save_cfg(self):
        try:
            with open(self.cfg_file, "w", encoding="utf-8") as f:
                json.dump({"enabled": self.enabled, "push_enabled": self.push_enabled,
                           "voice_enabled": self.voice_enabled, "grace": self.grace,
                           "remind_every": self.remind_every,
                           "compliance": self.compliance, "cheer_every": self.cheer_every,
                           "distract": self.distract, "work": self.work}, f)
        except Exception:
            pass
    def apply_settings(self, enabled, push, voice, grace, remind, compliance, cheer, distract, work):
        self.enabled = enabled
        self.push_enabled = push
        self.voice_enabled = voice
        self.grace = grace
        self.remind_every = remind
        self.compliance = compliance
        self.cheer_every = cheer
        self.distract = distract
        self.work = work
        self.save_cfg()
        if not enabled:
            self.context.emit("off", "")
    def set_enabled(self, on):
        self.enabled = on
        self.save_cfg()
        if not on:
            self.context.emit("off", "")
    def _detect_app(self, title):
        for key, name in APP_NAMES:
            if key in title:
                return name
        return None
    def _detect_distract(self, title):
        for key in self.distract:
            if key in title:
                return DISTRACT_NAMES.get(key, key.capitalize())
        return None
    def _poll(self):
        if not self.enabled:
            return
        title = get_foreground_title()
        low = title.lower()
        if not title or "kai" in low or "кай" in low:
            cat = "self"
        elif self._detect_distract(low):
            cat = "distract"
        elif any(k in low for k in self.work):
            cat = "work"
        elif any(k in low for k in BROWSER_KEYS):
            cat = "browse"
        else:
            cat = "neutral"
        if (cat, title) != self._last_ctx:
            self._last_ctx = (cat, title)
            self.context.emit(cat, title)
        now = time.time()
        if cat != self.state:
            prev = self.state
            self.state = cat
            self.state_start = now
            self.remind_count = 0
            self.next_remind = now + self.grace
            if cat == "distract":
                self.distract_start = now
                self.cur_site = self._detect_distract(low) or "Сайт"
                self.alert.emit("sarcastic", self.bank.say("distract_now", site=self.cur_site))
                self.last_react = now
                self.remind_count = 1
                return
            if prev == "distract":
                dur = now - (self.distract_start or now)
                if dur <= self.compliance:
                    self.alert.emit("happy", self.bank.say("good_boy"))
                    self.reward.emit(15)
                    self.obeyed.emit()
                    if random.random() < 0.3:
                        self.alert.emit("excited", self.bank.say("good_boy_bonus"))
                        self.reward.emit(25)
                else:
                    self.alert.emit("happy", self.bank.say("welcome_back"))
                    self.reward.emit(5)
                self.last_react = now
            if cat == "work":
                self.next_cheer = now + self.cheer_every
                if now - self.last_react >= 30:
                    app = self._detect_app(low) or "рабочая прога"
                    self.alert.emit("excited", self.bank.say("praise_work", app=app))
                    self.last_react = now
            elif cat == "browse" and now - self.last_react >= 30:
                self.alert.emit("sarcastic", self.bank.say("browse_tease"))
                self.last_react = now
            return
        dur = now - self.state_start
        if cat == "distract":
            if now >= self.next_remind:
                self.alert.emit("worried", self.bank.say("distract_repeat",
                                                          min=int(dur // 60), site=self.cur_site))
                self.remind_count += 1
                self.next_remind = now + self.remind_every
        elif cat == "work":
            self.work_seconds += 5
            if now >= self.next_cheer:
                self.alert.emit("excited", self.bank.say("work_keep"))
                self.next_cheer = now + self.cheer_every + random.randint(-30, 30)
            if self.work_seconds >= 25 * 60:
                self.work_seconds = 0
                self.work_block.emit(25)

# ============================================
# ГОЛОСОВОЙ ДВИЖОК: GEMINI + EDGE + SYS
# ============================================
class VoiceEngine:
    def __init__(self, data_dir):
        self.voice_file = Path(data_dir) / "voice.json"
        cfg = self._load_cfg()
        self.engine = cfg.get("engine", "edge")
        self.gemini_key = cfg.get("gemini_key", "")
        self.gemini_voice = cfg.get("gemini_voice", "Leda")
        self.styles = dict(STYLE_PROMPTS)
        self.styles.update(cfg.get("styles", {}))
        self.voice_id = cfg.get("voice_id", "ru-RU-SvetlanaNeural")
        self.pitch_hz = cfg.get("pitch_hz", 0)
        self.rate_extra = cfg.get("rate_extra", 0)
        self.emotion_fx = cfg.get("emotion_fx", True)
        self._queue = queue.Queue()
        self._pygame_ok = False
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._gclient = None
        self._gclient_key = None
        try:
            import edge_tts
            self._edge_ok = True
        except ImportError:
            self._edge_ok = False
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()
    def _load_cfg(self):
        try:
            if self.voice_file.exists():
                with open(self.voice_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    def _save_cfg(self):
        try:
            with open(self.voice_file, "w", encoding="utf-8") as f:
                json.dump({"engine": self.engine, "gemini_key": self.gemini_key,
                           "gemini_voice": self.gemini_voice, "styles": self.styles,
                           "voice_id": self.voice_id, "pitch_hz": self.pitch_hz,
                           "rate_extra": self.rate_extra, "emotion_fx": self.emotion_fx}, f)
        except Exception:
            pass
    def set_config(self, engine, gemini_key, gemini_voice, voice_id, pitch_hz, rate_extra):
        self.engine = engine
        self.gemini_key = gemini_key.strip()
        self.gemini_voice = gemini_voice
        self.voice_id = voice_id
        self.pitch_hz = pitch_hz
        self.rate_extra = rate_extra
        self._gclient = None
        self._clear_cache()
        self._save_cfg()
    def set_styles(self, styles):
        self.styles = dict(styles)
        self._clear_cache()
        self._save_cfg()
    def set_emotion_fx(self, on):
        self.emotion_fx = on
        self._save_cfg()
    def current_params(self):
        return (self.voice_id, self.pitch_hz, self.rate_extra)
    @staticmethod
    def _edge_params(rate_pct, params):
        voice_id, pitch_hz, rate_extra = params
        total = rate_pct + rate_extra
        rate_str = f"{'+' if total >= 0 else ''}{total}%"
        pitch_str = f"{'+' if pitch_hz >= 0 else ''}{pitch_hz}Hz"
        return voice_id, rate_str, pitch_str
    def speak(self, text, block=False, rate_pct=0, emotion="neutral"):
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        ev = threading.Event() if block else None
        self._queue.put((cleaned, ev, rate_pct, self.current_params(), emotion))
        if block:
            ev.wait(timeout=180)
    def prepare(self, text, rate_pct=0, emotion="caring"):
        cleaned = clean_for_speech(text)
        if not cleaned:
            return
        threading.Thread(target=self._prepare_sync,
                         args=(cleaned, rate_pct, emotion), daemon=True).start()
    def _prepare_sync(self, text, rate_pct, emotion):
        try:
            if self.engine == "gemini" and self.gemini_key:
                self._gemini_generate(text, emotion)
            else:
                params = self.current_params()
                if params[0] is None:
                    return
                key = ("edge", text, rate_pct, params)
                with self._cache_lock:
                    if key in self._cache:
                        return
                import edge_tts
                voice_id, rate_str, pitch_str = self._edge_params(rate_pct, params)
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                asyncio.run(edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str).save(path))
                with self._cache_lock:
                    self._cache[key] = path
        except Exception:
            pass
    def _clear_cache(self):
        with self._cache_lock:
            for path in self._cache.values():
                try:
                    os.remove(path)
                except Exception:
                    pass
            self._cache.clear()
    def clear(self):
        try:
            while True:
                self._queue.get_nowait()
        except queue.Empty:
            pass
        try:
            if self._pygame_ok:
                import pygame
                pygame.mixer.music.stop()
        except Exception:
            pass
        self._clear_cache()
    def _ensure_pygame(self):
        import pygame
        if not self._pygame_ok:
            pygame.mixer.init()
            self._pygame_ok = True
        return pygame
    def _play_file(self, path):
        pygame = self._ensure_pygame()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    # --- GEMINI ---
    def _gemini_client(self):
        from google import genai
        if self._gclient is None or self._gclient_key != self.gemini_key:
            self._gclient = genai.Client(api_key=self.gemini_key)
            self._gclient_key = self.gemini_key
        return self._gclient
    def _gemini_generate(self, text, emotion):
        """Генерирует wav через Gemini TTS, кладёт в кэш, возвращает путь"""
        key = ("gemini", text, emotion, self.gemini_voice)
        with self._cache_lock:
            if key in self._cache:
                return self._cache[key]
        from google.genai import types
        style = self.styles.get(emotion, STYLE_PROMPTS.get(emotion, ""))
        prompt = f"Скажи по-русски. Стиль: {style}. Текст: {text}"
        resp = self._gemini_client().models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=self.gemini_voice)))))
        part = resp.candidates[0].content.parts[0]
        data = part.inline_data.data
        mime = getattr(part.inline_data, "mime_type", "") or ""
        rate = 24000
        if "rate=" in mime:
            try:
                rate = int(mime.split("rate=")[1].split(";")[0])
            except Exception:
                pass
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(data)
        with self._cache_lock:
            self._cache[key] = path
        return path
    def _speak_gemini(self, text, emotion):
        if not self.gemini_key:
            return False
        try:
            path = self._gemini_generate(text, emotion)
            owned = False
            self._play_file(path)
            return True
        except Exception as e:
            print("Gemini TTS error:", e)
            return False
    # --- EDGE ---
    def _apply_fx(self, src, emotion):
        if not self.emotion_fx:
            return src
        st, speed, vol = EMOTION_FX.get(emotion, (0, 1.0, 1.0))
        if st == 0 and speed == 1.0 and vol == 1.0:
            return src
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return src
        f = 2 ** (st / 12.0)
        fd, dst = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        tempo = max(0.5, min(2.0, speed / f))
        filt = f"asetrate=24000*{f:.4f},aresample=24000,atempo={tempo:.4f},volume={vol:.2f}"
        try:
            subprocess.run([exe, "-y", "-i", src, "-af", filt, dst],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            return dst
        except Exception:
            try:
                os.remove(dst)
            except Exception:
                pass
            return src
    def _speak_edge(self, text, rate_pct, params, emotion):
        voice_id, rate_str, pitch_str = self._edge_params(rate_pct, params)
        if not self._edge_ok or voice_id is None:
            return False
        try:
            key = ("edge", text, rate_pct, params)
            with self._cache_lock:
                path = self._cache.pop(key, None)
            owned = path is None
            if owned:
                import edge_tts
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd)
                try:
                    asyncio.run(edge_tts.Communicate(text, voice_id, rate=rate_str, pitch=pitch_str).save(path))
                except Exception:
                    os.remove(path)
                    return False
            play_path = self._apply_fx(path, emotion)
            try:
                self._play_file(play_path)
            finally:
                if play_path != path:
                    try:
                        os.remove(play_path)
                    except Exception:
                        pass
                if owned:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
            return True
        except Exception:
            return False
    def _speak_sys(self, text, tts, rate_pct, params, emotion):
        try:
            if tts is None:
                import pyttsx3
                tts = pyttsx3.init()
            st, speed, vol = EMOTION_FX.get(emotion, (0, 1.0, 1.0))
            total = rate_pct + params[2]
            tts.setProperty("rate", max(100, int((200 + total * 2 + st * 10) * speed)))
            tts.setProperty("volume", vol)
            tts.say(text)
            tts.runAndWait()
        except Exception:
            pass
        return tts
    def _loop(self):
        tts = None
        while True:
            text, ev, rate_pct, params, emotion = self._queue.get()
            try:
                ok = False
                if self.engine == "gemini":
                    ok = self._speak_gemini(text, emotion)
                if not ok:
                    ok = self._speak_edge(text, rate_pct, params, emotion)
                if not ok:
                    tts = self._speak_sys(text, tts, rate_pct, params, emotion)
            except Exception as e:
                print("Voice error:", e)
            finally:
                if ev:
                    ev.set()

# ============================================
# КОМПАНЬОН КАЙ
# ============================================
class Companion(QObject):
    message = pyqtSignal(str, str)
    def __init__(self, voice_engine, bank):
        super().__init__()
        self.voice = voice_engine
        self.bank = bank
        self.rate_pct = 30
        self.pause_per_char = 0.02
    def set_speed_value(self, value):
        self.rate_pct = 50 - 2 * value
        self.pause_per_char = value * 0.002
    def say(self, emotion, text):
        self.message.emit(emotion, text)
    def say_aloud(self, emotion, text):
        self.message.emit(emotion, text)
        self.voice.speak(text, block=False, rate_pct=0, emotion=emotion)
    def speak_with_pause(self, text, emotion="caring"):
        self.voice.speak(text, block=True, rate_pct=self.rate_pct, emotion=emotion)
        time.sleep(max(1.0, len(text) * self.pause_per_char))
    def greet(self):
        self.say_aloud("neutral", self.bank.say("greet"))
    def on_project_created(self, name):
        self.say_aloud("excited", self.bank.say("project_created", name=name))
    def on_task_created(self, name):
        self.say("happy", self.bank.say("task_created", name=name))
    def on_rehearsal_start(self, name, mode):
        key = "rehearsal_intro_voice" if mode == "voice" else "rehearsal_intro_manual"
        if mode == "voice":
            self.say_aloud("excited", self.bank.say(key, name=name))
        else:
            self.say("excited", self.bank.say(key, name=name))
    def reh_line1(self):
        return self.bank.say("reh_line1")
    def reh_line2(self):
        return self.bank.say("reh_line2")
    def reh_step(self, i, step):
        return self.bank.say("reh_step", i=i, step=step)
    def reh_end(self):
        return self.bank.say("reh_end")
    def on_rehearsal_done(self):
        self.say_aloud("happy", self.bank.say("rehearsal_done"))
    def on_task_done(self, name):
        self.say_aloud("happy", self.bank.say("task_done", name=name))
    def on_task_undone(self):
        self.say("neutral", self.bank.say("task_undone"))
    def on_level_up(self, level):
        self.say_aloud("excited", self.bank.say("level_up", level=level))
    def on_deleted(self):
        self.say("neutral", self.bank.say("deleted"))
    def on_renamed(self):
        self.say("neutral", self.bank.say("renamed"))
    def on_steps_updated(self):
        self.say("happy", self.bank.say("steps_updated"))
    def on_empty_steps(self):
        self.say("worried", self.bank.say("empty_steps"))
    def on_enemy_hit(self, name, amount, hp_left):
        self.say("sarcastic", self.bank.say("enemy_hit", name=name, amount=amount, hp_left=hp_left))
    def on_enemy_defeated(self, name):
        self.say_aloud("excited", self.bank.say("enemy_defeated", name=name))
    def on_quest_done(self, reward):
        self.say("happy", self.bank.say("quest_done", reward=reward))
    def on_work_block(self, minutes):
        self.say_aloud("excited", self.bank.say("work_block", minutes=minutes))

# ============================================
# СТИЛИ
# ============================================
STYLESHEET = """
QMainWindow { background-color: #1a1a2e; }
QWidget { background-color: #1a1a2e; }
QLabel { color: #eaeaea; font-size: 14px; }
QPushButton {
    background-color: #16213e; color: #eaeaea;
    border: 2px solid #0f3460; border-radius: 8px;
    padding: 12px 20px; font-size: 14px;
}
QPushButton:hover { background-color: #0f3460; }
QPushButton:pressed { background-color: #533483; }
QPushButton:checked { background-color: #533483; border-color: #eaeaea; }
QPushButton:disabled { background-color: #22223a; color: #555; }
QLineEdit, QPlainTextEdit {
    background-color: #0f3460; color: #ffffff;
    border: 2px solid #533483; border-radius: 5px;
    padding: 10px; font-size: 14px;
}
QListWidget {
    background-color: #0f3460; color: #eaeaea;
    border: 2px solid #533483; border-radius: 5px;
    font-size: 15px; padding: 5px;
}
QListWidget::item { padding: 10px; }
QListWidget::item:selected { background-color: #533483; border-radius: 5px; }
QFrame { background-color: #16213e; border-radius: 12px; padding: 15px; }
QSlider::groove:horizontal {
    border: 1px solid #0f3460; height: 8px;
    background: #0f3460; border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #533483; border: 2px solid #eaeaea;
    width: 20px; margin: -6px 0; border-radius: 10px;
}
QProgressBar {
    border: 2px solid #0f3460; border-radius: 5px;
    text-align: center; color: #eaeaea; height: 18px;
    background-color: #0f3460;
}
QProgressBar::chunk { background-color: #533483; border-radius: 3px; }
QComboBox {
    background-color: #0f3460; color: #eaeaea;
    border: 2px solid #533483; border-radius: 5px;
    padding: 4px 8px; font-size: 12px;
}
QComboBox QAbstractItemView {
    background-color: #16213e; color: #eaeaea;
    selection-background-color: #533483;
}
QMessageBox { background-color: #1a1a2e; }
QScrollArea { border: none; background: transparent; }
QCheckBox { color: #eaeaea; font-size: 14px; }
QCheckBox::indicator { width: 18px; height: 18px; }
QSpinBox {
    background-color: #0f3460; color: #eaeaea;
    border: 2px solid #533483; border-radius: 5px; padding: 5px;
}
QMenu { background-color: #16213e; color: #eaeaea; border: 2px solid #0f3460; }
QMenu::item:selected { background-color: #533483; }
"""

# ============================================
# РЕДАКТОР ШАГОВ
# ============================================
class StepsDialog(QDialog):
    def __init__(self, parent=None, initial=None):
        super().__init__(parent)
        self.setWindowTitle("👣 Шаги задачи")
        self.setGeometry(350, 150, 600, 500)
        self.setStyleSheet(STYLESHEET)
        self.rows = []
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        hint = QLabel("Каждый шаг — отдельная строка. Номера проставляются сами.")
        hint.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        layout.addWidget(hint)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.container)
        self.rows_layout.setSpacing(8)
        self.rows_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        btn_add = QPushButton("➕ Добавить шаг")
        btn_add.clicked.connect(lambda: self._add_row(""))
        layout.addWidget(btn_add)
        if initial:
            for s in initial:
                self._add_row(s)
        else:
            self._add_row("")
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("💾 Сохранить")
        btn_ok.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
    def _add_row(self, text=""):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        num = QLabel("")
        num.setFixedWidth(30)
        num.setStyleSheet("font-size: 14px; font-weight: bold; color: #533483; background: transparent;")
        edit = QLineEdit(text)
        edit.setPlaceholderText("Опиши шаг...")
        btn_del = QPushButton("✖")
        btn_del.setFixedWidth(40)
        btn_del.clicked.connect(lambda _, r=row: self._remove_row(r))
        hl.addWidget(num)
        hl.addWidget(edit)
        hl.addWidget(btn_del)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self.rows.append(row)
        self._renumber()
        edit.setFocus()
    def _remove_row(self, row):
        if row in self.rows:
            self.rows.remove(row)
            row.deleteLater()
            self._renumber()
    def _renumber(self):
        for i, row in enumerate(self.rows, 1):
            lbl = row.findChild(QLabel)
            if lbl:
                lbl.setText(f"{i}.")
    def get_steps(self):
        steps = []
        for row in self.rows:
            edit = row.findChild(QLineEdit)
            if edit:
                text = edit.text().strip()
                if text:
                    steps.append(text)
        return steps

# ============================================
# ТОСТ
# ============================================
class Toast(QWidget):
    closed = pyqtSignal(object)
    def __init__(self, title, text):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #533483;
                border: 2px solid #eaeaea;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        fl = QVBoxLayout(frame)
        t = QLabel(title)
        t.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; background: transparent;")
        fl.addWidget(t)
        d = QLabel(text)
        d.setStyleSheet("font-size: 12px; color: #eaeaea; background: transparent;")
        d.setWordWrap(True)
        fl.addWidget(d)
        layout.addWidget(frame)
        self.setFixedWidth(320)
        QTimer.singleShot(5000, self.close)
    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)

# ============================================
# НАВИГАЦИЯ
# ============================================
class NavBar(QWidget):
    tab_changed = pyqtSignal(str)
    minimize_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #16213e; border-bottom: 2px solid #0f3460;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)
        self.btn_tasks = QPushButton("📋 Задачи")
        self.btn_game = QPushButton("🎮 Игра")
        self.btn_settings = QPushButton("⚙ Настройки")
        for b in (self.btn_tasks, self.btn_game, self.btn_settings):
            b.setCheckable(True)
            b.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px 25px;")
        self.btn_tasks.clicked.connect(lambda: self.tab_changed.emit("tasks"))
        self.btn_game.clicked.connect(lambda: self.tab_changed.emit("game"))
        self.btn_settings.clicked.connect(lambda: self.tab_changed.emit("settings"))
        layout.addWidget(self.btn_tasks)
        layout.addWidget(self.btn_game)
        layout.addWidget(self.btn_settings)
        layout.addStretch()
        self.btn_min = QPushButton("⬇")
        self.btn_min.setFixedWidth(45)
        self.btn_min.setToolTip("Свернуть в трей")
        self.btn_min.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_min.clicked.connect(self.minimize_requested.emit)
        layout.addWidget(self.btn_min)
        self.set_active("tasks")
    def set_active(self, name):
        self.btn_tasks.setChecked(name == "tasks")
        self.btn_game.setChecked(name == "game")
        self.btn_settings.setChecked(name == "settings")

# ============================================
# ВКЛАДКА НАСТРОЕК
# ============================================
class SettingsPage(QWidget):
    avatar_changed = pyqtSignal()
    def __init__(self, monitor, voice, avatar, companion, bank):
        super().__init__()
        self.monitor = monitor
        self.voice = voice
        self.avatar = avatar
        self.companion = companion
        self.bank = bank
        self.previews = {}
        self._init_ui()
    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 20, 30, 20)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        title = QLabel("⚙ Настройки Кая")
        title.setStyleSheet("font-size: 26px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        # --- МОНИТОРИНГ ---
        mon_frame = QFrame()
        mf = QVBoxLayout(mon_frame)
        mt = QLabel("👁 Мониторинг и дрессировка")
        mt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        mf.addWidget(mt)
        self.chk_monitor = QCheckBox("Следить за активными окнами")
        mf.addWidget(self.chk_monitor)
        self.chk_push = QCheckBox("Пуш-уведомления Windows")
        mf.addWidget(self.chk_push)
        self.chk_voice = QCheckBox("Озвучивать уведомления голосом")
        mf.addWidget(self.chk_voice)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Считать послушанием, если вышел за (сек):"))
        self.spin_compliance = QSpinBox(); self.spin_compliance.setRange(10, 600)
        row1.addWidget(self.spin_compliance); row1.addStretch()
        mf.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Повторные напоминания каждые (сек):"))
        self.spin_grace = QSpinBox(); self.spin_grace.setRange(10, 600)
        row2.addWidget(self.spin_grace); row2.addStretch()
        mf.addLayout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Подбадривать во время работы каждые (сек):"))
        self.spin_cheer = QSpinBox(); self.spin_cheer.setRange(60, 1800)
        row3.addWidget(self.spin_cheer); row3.addStretch()
        mf.addLayout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Реакции на смены окон не чаще (сек):"))
        self.spin_remind = QSpinBox(); self.spin_remind.setRange(10, 600)
        row4.addWidget(self.spin_remind); row4.addStretch()
        mf.addLayout(row4)
        mf.addWidget(QLabel("Отвлекающие слова (через запятую):"))
        self.edit_distract = QLineEdit()
        mf.addWidget(self.edit_distract)
        mf.addWidget(QLabel("Рабочие программы (через запятую):"))
        self.edit_work = QLineEdit()
        mf.addWidget(self.edit_work)
        btn_save_mon = QPushButton("💾 Сохранить мониторинг")
        btn_save_mon.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_mon.clicked.connect(self._save_monitor)
        mf.addWidget(btn_save_mon)
        layout.addWidget(mon_frame)
        # --- ГОЛОС / ДВИЖОК ---
        voice_frame = QFrame()
        vf = QVBoxLayout(voice_frame)
        vt = QLabel("🎙 Голос и движок озвучки")
        vt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        vf.addWidget(vt)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["edge-tts (быстрый, без ключа)",
                                    "Gemini TTS (живые интонации по описанию)"])
        vf.addWidget(self.engine_combo)
        vf.addWidget(QLabel("API-ключ Gemini (AIza...):"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Вставь ключ из aistudio.google.com → Get API key")
        vf.addWidget(self.key_edit)
        vf.addWidget(QLabel("Тембр Gemini:"))
        self.gvoice_combo = QComboBox()
        self.gvoice_combo.addItems(GEMINI_VOICES)
        vf.addWidget(self.gvoice_combo)
        self.chk_emotion = QCheckBox("🎭 Доп. окраска edge-голоса (ffmpeg), когда Gemini недоступен")
        self.chk_emotion.toggled.connect(self.voice.set_emotion_fx)
        vf.addWidget(self.chk_emotion)
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["👩 Светлана", "👨 Дмитрий", "🤖 Системный (офлайн)"])
        vf.addWidget(self.voice_combo)
        preset_layout = QHBoxLayout()
        for label, vid, pitch, rate in [
            ("🎙 Стандарт", 0, 0, 0), ("🎀 Фембой", 1, 50, 10), ("🥺 Милый", 0, 35, 5)]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, v=vid, p=pitch, r=rate: self._apply_preset(v, p, r))
            preset_layout.addWidget(b)
        vf.addLayout(preset_layout)
        vf.addWidget(QLabel("Высота edge-голоса (pitch):"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-50, 80)
        vf.addWidget(self.pitch_slider)
        self.pitch_label = QLabel("")
        self.pitch_label.setStyleSheet("color: #888; background: transparent;")
        self.pitch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vf.addWidget(self.pitch_label)
        self.pitch_slider.valueChanged.connect(self._update_voice_labels)
        vf.addWidget(QLabel("Доп. темп edge-речи (%):"))
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(-30, 30)
        vf.addWidget(self.rate_slider)
        self.rate_label = QLabel("")
        self.rate_label.setStyleSheet("color: #888; background: transparent;")
        self.rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vf.addWidget(self.rate_label)
        self.rate_slider.valueChanged.connect(self._update_voice_labels)
        vbtn_layout = QHBoxLayout()
        btn_test = QPushButton("🔊 Тест")
        btn_test.clicked.connect(self._test_voice)
        vbtn_layout.addWidget(btn_test)
        btn_save_voice = QPushButton("💾 Применить голос")
        btn_save_voice.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_voice.clicked.connect(self._save_voice)
        vbtn_layout.addWidget(btn_save_voice)
        vf.addLayout(vbtn_layout)
        layout.addWidget(voice_frame)
        # --- УСЛОВИЯ РЕЧИ (стили Gemini) ---
        style_frame = QFrame()
        sf2 = QVBoxLayout(style_frame)
        stt = QLabel(" Условия речи (как говорить, по эмоциям)")
        stt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        sf2.addWidget(stt)
        shint = QLabel("Описание манеры для Gemini TTS. Редактируй под себя.")
        shint.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        sf2.addWidget(shint)
        self.style_combo = QComboBox()
        for key, label in EMOTIONS_RU.items():
            self.style_combo.addItem(label, key)
        self.style_combo.currentIndexChanged.connect(self._load_style_event)
        sf2.addWidget(self.style_combo)
        self.style_edit = QPlainTextEdit()
        self.style_edit.setFixedHeight(90)
        sf2.addWidget(self.style_edit)
        sbtn = QHBoxLayout()
        btn_save_style = QPushButton("💾 Сохранить манеру")
        btn_save_style.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_style.clicked.connect(self._save_style)
        sbtn.addWidget(btn_save_style)
        btn_reset_style = QPushButton("↩ Сбросить")
        btn_reset_style.clicked.connect(self._reset_style)
        sbtn.addWidget(btn_reset_style)
        sf2.addLayout(sbtn)
        layout.addWidget(style_frame)
        # --- ФРАЗЫ ---
        phr_frame = QFrame()
        pf = QVBoxLayout(phr_frame)
        pt = QLabel("💬 Фразы Кая")
        pt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        pf.addWidget(pt)
        phint = QLabel("Каждая строка — вариант фразы, выбирается случайно.\nПлейсхолдеры: {app}, {site}, {min}, {name}, {level}, {i}, {step}, {minutes}, {amount}, {hp_left}, {reward}")
        phint.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        pf.addWidget(phint)
        self.phr_combo = QComboBox()
        for key, label in EVENT_LABELS:
            self.phr_combo.addItem(label, key)
        self.phr_combo.currentIndexChanged.connect(self._load_phrase_event)
        pf.addWidget(self.phr_combo)
        self.phr_edit = QPlainTextEdit()
        self.phr_edit.setFixedHeight(140)
        pf.addWidget(self.phr_edit)
        pbtn = QHBoxLayout()
        btn_save_phr = QPushButton("💾 Сохранить фразы")
        btn_save_phr.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_phr.clicked.connect(self._save_phrases)
        pbtn.addWidget(btn_save_phr)
        btn_reset_phr = QPushButton("↩ Сбросить на стандарт")
        btn_reset_phr.clicked.connect(self._reset_phrases)
        pbtn.addWidget(btn_reset_phr)
        pf.addLayout(pbtn)
        layout.addWidget(phr_frame)
        # --- СПРАЙТЫ ---
        spr_frame = QFrame()
        sf = QVBoxLayout(spr_frame)
        st = QLabel("🖼 Спрайты аватара")
        st.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        sf.addWidget(st)
        for em in self.avatar.emotions:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            name = QLabel(EMOTIONS_RU[em])
            name.setFixedWidth(130)
            name.setStyleSheet("background: transparent;")
            hl.addWidget(name)
            prev = QLabel()
            prev.setFixedSize(44, 44)
            prev.setStyleSheet("background: #0f3460; border-radius: 6px;")
            prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.previews[em] = prev
            hl.addWidget(prev)
            btn_pick = QPushButton("Выбрать...")
            btn_pick.clicked.connect(lambda _, e=em: self._pick(e))
            hl.addWidget(btn_pick)
            btn_del = QPushButton("✖")
            btn_del.setFixedWidth(40)
            btn_del.clicked.connect(lambda _, e=em: self._remove_sprite(e))
            hl.addWidget(btn_del)
            hl.addStretch()
            sf.addWidget(row)
        btn_folder = QPushButton("📂 Открыть папку спрайтов")
        btn_folder.clicked.connect(self._open_folder)
        sf.addWidget(btn_folder)
        layout.addWidget(spr_frame)
        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
    def sync(self):
        m = self.monitor
        self.chk_monitor.setChecked(m.enabled)
        self.chk_push.setChecked(m.push_enabled)
        self.chk_voice.setChecked(m.voice_enabled)
        self.spin_compliance.setValue(m.compliance)
        self.spin_grace.setValue(m.remind_every)
        self.spin_cheer.setValue(m.cheer_every)
        self.spin_remind.setValue(m.grace)
        self.edit_distract.setText(", ".join(m.distract))
        self.edit_work.setText(", ".join(m.work))
        self.engine_combo.setCurrentIndex(1 if self.voice.engine == "gemini" else 0)
        self.key_edit.setText(self.voice.gemini_key)
        idx = GEMINI_VOICES.index(self.voice.gemini_voice) if self.voice.gemini_voice in GEMINI_VOICES else 0
        self.gvoice_combo.setCurrentIndex(idx)
        self.chk_emotion.setChecked(self.voice.emotion_fx)
        if self.voice.voice_id == "ru-RU-DmitryNeural":
            self.voice_combo.setCurrentIndex(1)
        elif self.voice.voice_id is None:
            self.voice_combo.setCurrentIndex(2)
        else:
            self.voice_combo.setCurrentIndex(0)
        self.pitch_slider.setValue(self.voice.pitch_hz)
        self.rate_slider.setValue(self.voice.rate_extra)
        self._update_voice_labels()
        self._load_style_event()
        self._load_phrase_event()
        self._refresh_previews()
    def _load_style_event(self):
        key = self.style_combo.currentData()
        self.style_edit.setPlainText(self.voice.styles.get(key, STYLE_PROMPTS.get(key, "")))
    def _save_style(self):
        key = self.style_combo.currentData()
        self.voice.styles[key] = self.style_edit.toPlainText().strip()
        self.voice.set_styles(self.voice.styles)
        self.companion.say("happy", self.bank.say("settings_saved"))
    def _reset_style(self):
        self.voice.styles = dict(STYLE_PROMPTS)
        self.voice.set_styles(self.voice.styles)
        self._load_style_event()
    def _load_phrase_event(self):
        key = self.phr_combo.currentData()
        lines = self.bank.data.get(key) or DEFAULT_PHRASES.get(key) or []
        self.phr_edit.setPlainText("\n".join(lines))
    def _save_phrases(self):
        key = self.phr_combo.currentData()
        lines = [l.strip() for l in self.phr_edit.toPlainText().split("\n") if l.strip()]
        if lines:
            self.bank.data[key] = lines
            self.bank.save()
            self.companion.say("happy", self.bank.say("settings_saved"))
    def _reset_phrases(self):
        self.bank.reset()
        self._load_phrase_event()
    def _refresh_previews(self):
        emojis = {"neutral": "😐", "happy": "😊", "worried": "😟",
                  "sarcastic": "😏", "excited": "🤩", "caring": "💜"}
        for em, prev in self.previews.items():
            pix = self.avatar.pixmap_for(em, 40)
            if pix:
                prev.setPixmap(pix)
                prev.setText("")
            else:
                prev.clear()
                prev.setText(emojis[em])
    def _save_monitor(self):
        self.monitor.apply_settings(
            self.chk_monitor.isChecked(), self.chk_push.isChecked(),
            self.chk_voice.isChecked(), self.spin_remind.value(),
            self.spin_grace.value(), self.spin_compliance.value(),
            self.spin_cheer.value(),
            [s.strip().lower() for s in self.edit_distract.text().split(",") if s.strip()],
            [s.strip().lower() for s in self.edit_work.text().split(",") if s.strip()])
        self.companion.say("happy", self.bank.say("settings_saved"))
    def _apply_preset(self, voice_idx, pitch, rate):
        self.voice_combo.setCurrentIndex(voice_idx)
        self.pitch_slider.setValue(pitch)
        self.rate_slider.setValue(rate)
    def _update_voice_labels(self):
        self.pitch_label.setText(f"{self.pitch_slider.value():+d} Hz")
        self.rate_label.setText(f"{self.rate_slider.value():+d}%")
    def _current_voice_id(self):
        idx = self.voice_combo.currentIndex()
        if idx == 0:
            return "ru-RU-SvetlanaNeural"
        if idx == 1:
            return "ru-RU-DmitryNeural"
        return None
    def _test_voice(self):
        self.voice.clear()
        self.voice.speak("Привет~ Я Кай. Ну как тебе мой голос, м?.. 💋",
                         block=False, emotion="caring")
    def _save_voice(self):
        self.voice.set_config(
            "gemini" if self.engine_combo.currentIndex() == 1 else "edge",
            self.key_edit.text(),
            self.gvoice_combo.currentText(),
            self._current_voice_id(),
            self.pitch_slider.value(),
            self.rate_slider.value())
        self.voice.speak(self.bank.say("voice_saved"), block=False, emotion="caring")
    def _pick(self, emotion):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Спрайт для эмоции «{EMOTIONS_RU[emotion]}»", "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp)")
        if path:
            self.avatar.set_from_file(emotion, path)
            self._refresh_previews()
            self.avatar_changed.emit()
    def _remove_sprite(self, emotion):
        self.avatar.remove(emotion)
        self._refresh_previews()
        self.avatar_changed.emit()
    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.avatar.dir)))

# ============================================
# ЭКРАН ПРОЕКТОВ
# ============================================
class ProjectsPage(QWidget):
    project_selected = pyqtSignal(int)
    project_created = pyqtSignal(str)
    project_deleted = pyqtSignal()
    project_renamed = pyqtSignal()
    def __init__(self, data_manager):
        super().__init__()
        self.data = data_manager
        self._init_ui()
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("🎯 Мои проекты")
        title.setStyleSheet("font-size: 28px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.btn_new = QPushButton("➕ Новый проект")
        self.btn_new.setStyleSheet("background-color: #533483; font-size: 16px; font-weight: bold; padding: 15px;")
        self.btn_new.clicked.connect(self._create_project)
        layout.addWidget(self.btn_new)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_project)
        layout.addWidget(self.list)
        edit_layout = QHBoxLayout()
        btn_rename = QPushButton("✏️ Переименовать")
        btn_rename.clicked.connect(self._rename_project)
        edit_layout.addWidget(btn_rename)
        btn_delete = QPushButton("🗑 Удалить")
        btn_delete.clicked.connect(self._delete_project)
        edit_layout.addWidget(btn_delete)
        layout.addLayout(edit_layout)
        hint = QLabel("💡 Двойной клик по проекту → открыть")
        hint.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
    def refresh(self):
        self.list.clear()
        for project in self.data.get_projects():
            done = sum(1 for t in project["tasks"] if t["done"])
            total = len(project["tasks"])
            item = QListWidgetItem(f"📁 {project['name']}  ({done}/{total})")
            item.setData(Qt.ItemDataRole.UserRole, project["id"])
            self.list.addItem(item)
    def _selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
    def _create_project(self):
        name, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if ok and name.strip():
            self.data.create_project(name.strip())
            self.refresh()
            self.project_created.emit(name.strip())
    def _rename_project(self):
        pid = self._selected_id()
        if pid is None:
            return
        p = self.data.get_project(pid)
        name, ok = QInputDialog.getText(self, "Переименовать", "Новое название:", text=p["name"])
        if ok and name.strip():
            self.data.rename_project(pid, name.strip())
            self.refresh()
            self.project_renamed.emit()
    def _delete_project(self):
        pid = self._selected_id()
        if pid is None:
            return
        p = self.data.get_project(pid)
        reply = QMessageBox.question(self, "Удалить проект",
                                     f"Удалить проект '{p['name']}' со всеми задачами?")
        if reply == QMessageBox.StandardButton.Yes:
            self.data.delete_project(pid)
            self.refresh()
            self.project_deleted.emit()
    def _open_project(self, item):
        self.project_selected.emit(item.data(Qt.ItemDataRole.UserRole))

# ============================================
# ЭКРАН ПРОЕКТА
# ============================================
class ProjectPage(QWidget):
    back_requested = pyqtSignal()
    task_selected = pyqtSignal(int, int)
    task_created = pyqtSignal(str)
    task_deleted = pyqtSignal()
    task_renamed = pyqtSignal()
    def __init__(self, data_manager, companion):
        super().__init__()
        self.data = data_manager
        self.companion = companion
        self.current_project_id = None
        self._init_ui()
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        btn_back = QPushButton("← Назад к проектам")
        btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(btn_back)
        self.title = QLabel("📁 Проект")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        self.btn_new = QPushButton("➕ Новая задача")
        self.btn_new.setStyleSheet("background-color: #533483; font-weight: bold; padding: 12px;")
        self.btn_new.clicked.connect(self._create_task)
        layout.addWidget(self.btn_new)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_task)
        layout.addWidget(self.list)
        edit_layout = QHBoxLayout()
        btn_rename = QPushButton("✏️ Переименовать")
        btn_rename.clicked.connect(self._rename_task)
        edit_layout.addWidget(btn_rename)
        btn_delete = QPushButton("🗑 Удалить")
        btn_delete.clicked.connect(self._delete_task)
        edit_layout.addWidget(btn_delete)
        layout.addLayout(edit_layout)
        hint = QLabel("💡 Двойной клик → открыть задачу")
        hint.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
    def load_project(self, project_id):
        self.current_project_id = project_id
        p = self.data.get_project(project_id)
        if p:
            self.title.setText(f"📁 {p['name']}")
        self.refresh()
    def refresh(self):
        self.list.clear()
        p = self.data.get_project(self.current_project_id)
        if not p:
            return
        for task in p["tasks"]:
            mark = "✅" if task["done"] else "⬜"
            item = QListWidgetItem(f"{mark} {task['name']}  ({len(task['steps'])} шагов)")
            item.setData(Qt.ItemDataRole.UserRole, task["id"])
            self.list.addItem(item)
    def _selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None
    def _create_task(self):
        name, ok = QInputDialog.getText(self, "Новая задача", "Название задачи:")
        if not ok or not name.strip():
            return
        dlg = StepsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            steps = dlg.get_steps()
            if steps:
                self.data.create_task(self.current_project_id, name.strip(), steps)
                self.refresh()
                self.task_created.emit(name.strip())
            else:
                self.companion.on_empty_steps()
    def _rename_task(self):
        tid = self._selected_id()
        if tid is None:
            return
        t = self.data.get_task(self.current_project_id, tid)
        if not t:
            return
        name, ok = QInputDialog.getText(self, "Переименовать", "Новое название:", text=t["name"])
        if ok and name.strip():
            self.data.rename_task(self.current_project_id, tid, name.strip())
            self.refresh()
            self.task_renamed.emit()
    def _delete_task(self):
        tid = self._selected_id()
        if tid is None:
            return
        t = self.data.get_task(self.current_project_id, tid)
        if not t:
            return
        reply = QMessageBox.question(self, "Удалить задачу", f"Удалить задачу '{t['name']}'?")
        if reply == QMessageBox.StandardButton.Yes:
            self.data.delete_task(self.current_project_id, tid)
            self.refresh()
            self.task_deleted.emit()
    def _open_task(self, item):
        self.task_selected.emit(self.current_project_id, item.data(Qt.ItemDataRole.UserRole))

# ============================================
# ЭКРАН ЗАДАЧИ
# ============================================
class TaskPage(QWidget):
    back_requested = pyqtSignal()
    start_rehearsal = pyqtSignal(list, str, str)
    task_done_toggled = pyqtSignal(bool, str)
    steps_updated = pyqtSignal()
    def __init__(self, data_manager, companion):
        super().__init__()
        self.data = data_manager
        self.companion = companion
        self.current_project_id = None
        self.current_task_id = None
        self._init_ui()
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        btn_back = QPushButton("← Назад к проекту")
        btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(btn_back)
        self.title = QLabel("📝 Задача")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        steps_frame = QFrame()
        steps_layout = QVBoxLayout(steps_frame)
        steps_label = QLabel("👣 Шаги:")
        steps_label.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        steps_layout.addWidget(steps_label)
        self.steps_list = QListWidget()
        steps_layout.addWidget(self.steps_list)
        btn_steps = QPushButton("✏️ Редактировать шаги")
        btn_steps.clicked.connect(self._edit_steps)
        steps_layout.addWidget(btn_steps)
        layout.addWidget(steps_frame)
        btn_layout = QHBoxLayout()
        self.btn_done = QPushButton("⬜ Отметить выполненным")
        self.btn_done.clicked.connect(self._toggle_done)
        btn_layout.addWidget(self.btn_done)
        layout.addLayout(btn_layout)
        reh_layout = QHBoxLayout()
        btn_reh_voice = QPushButton("🎙 Репетиция с озвучкой")
        btn_reh_voice.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_reh_voice.clicked.connect(lambda: self._start_rehearsal("voice"))
        reh_layout.addWidget(btn_reh_voice)
        btn_reh_manual = QPushButton("🖐 Репетиция вручную")
        btn_reh_manual.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_reh_manual.clicked.connect(lambda: self._start_rehearsal("manual"))
        reh_layout.addWidget(btn_reh_manual)
        layout.addLayout(reh_layout)
        speed_frame = QFrame()
        speed_layout = QVBoxLayout(speed_frame)
        speed_title = QLabel("⚡ Скорость озвучки и пауз")
        speed_title.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent;")
        speed_layout.addWidget(speed_title)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 25)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_layout.addWidget(self.speed_label)
        self._on_speed_change(10)
        layout.addWidget(speed_frame)
    def load_task(self, project_id, task_id):
        self.current_project_id = project_id
        self.current_task_id = task_id
        self._refresh()
    def _refresh(self):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if not task:
            return
        self.title.setText(f"📝 {task['name']}")
        self.steps_list.clear()
        for i, step in enumerate(task["steps"], 1):
            self.steps_list.addItem(f"{i}. {step}")
        self.btn_done.setText("✅ Снять отметку" if task["done"] else "⬜ Отметить выполненным")
    def _edit_steps(self):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if not task:
            return
        dlg = StepsDialog(self, initial=task["steps"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            steps = dlg.get_steps()
            if steps:
                self.data.update_task_steps(self.current_project_id, self.current_task_id, steps)
                self._refresh()
                self.steps_updated.emit()
            else:
                self.companion.on_empty_steps()
    def _toggle_done(self):
        now_done = self.data.toggle_task_done(self.current_project_id, self.current_task_id)
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        self._refresh()
        self.task_done_toggled.emit(now_done, task["name"] if task else "")
    def _on_speed_change(self, value):
        self.companion.set_speed_value(value)
        rate = 50 - 2 * value
        pause_per_100 = value * 0.002 * 100
        if value <= 8:
            tempo = "Очень быстро"
        elif value <= 15:
            tempo = "Средне"
        else:
            tempo = "Спокойно"
        self.speed_label.setText(f"{tempo}: голос +{rate}%, пауза {pause_per_100:.0f} сек на 100 символов")
    def _start_rehearsal(self, mode):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if task and task["steps"]:
            self.start_rehearsal.emit(task["steps"], task["name"], mode)

# ============================================
# ЭКРАН РЕПЕТИЦИИ
# ============================================
class RehearsalPage(QWidget):
    finished = pyqtSignal()
    rehearsal_completed = pyqtSignal()
    _ui_step = pyqtSignal()
    _request_finish = pyqtSignal()
    def __init__(self, companion):
        super().__init__()
        self.companion = companion
        self.steps = []
        self.current_index = 0
        self.mode = "voice"
        self.is_running = False
        self._done = True
        self._ui_step.connect(self._show_current)
        self._request_finish.connect(self._finish_safe)
        self._init_ui()
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(50, 40, 50, 40)
        title = QLabel("🎭 РЕПЕТИЦИЯ")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #533483; background: transparent; letter-spacing: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)
        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("font-size: 13px; color: #888; background: transparent;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)
        layout.addSpacing(10)
        self.task_name = QLabel("")
        self.task_name.setStyleSheet("font-size: 16px; color: #888; background: transparent;")
        self.task_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.task_name)
        layout.addStretch()
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("font-size: 14px; color: #666; background: transparent;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        layout.addSpacing(20)
        self.current_step = QLabel("...")
        self.current_step.setStyleSheet("font-size: 36px; font-weight: bold; color: #eaeaea; background: transparent; padding: 30px;")
        self.current_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_step.setWordWrap(True)
        self.current_step.setMinimumHeight(180)
        layout.addWidget(self.current_step)
        layout.addSpacing(20)
        self.next_step_label = QLabel("")
        self.next_step_label.setStyleSheet("font-size: 16px; color: #666; background: transparent; font-style: italic;")
        self.next_step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_step_label.setWordWrap(True)
        layout.addWidget(self.next_step_label)
        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_stop = QPushButton("⏹ Остановить")
        self.btn_stop.clicked.connect(self._stop)
        btn_layout.addWidget(self.btn_stop)
        self.btn_next = QPushButton("Дальше →")
        self.btn_next.setStyleSheet("background-color: #533483; font-weight: bold; padding: 15px 30px;")
        self.btn_next.clicked.connect(self._next_step)
        btn_layout.addWidget(self.btn_next)
        layout.addLayout(btn_layout)
    def start(self, steps, task_name, mode):
        self.steps = steps
        self.mode = mode
        self.task_name.setText(f"📝 {task_name}")
        self.current_index = 0
        self.is_running = True
        self._done = False
        if mode == "voice":
            self.mode_label.setText("🎙 Авто-режим: Кай ведёт, листание отключено")
            self.btn_next.setEnabled(False)
            self.btn_stop.setText("⏹ Остановить")
            # предзагрузка первых реплик
            self.companion.voice.prepare(self.companion.reh_line1(), self.companion.rate_pct, "caring")
            threading.Thread(target=self._run_rehearsal, daemon=True).start()
        else:
            self.mode_label.setText("🖐 Ручной режим: листай сам, Кай молчит")
            self.btn_next.setEnabled(True)
            self.btn_stop.setText("⏹ Отменить")
            self._show_current()
    def _show_current(self):
        if not self.steps or self.current_index >= len(self.steps):
            return
        self.current_step.setText(self.steps[self.current_index])
        self.progress_label.setText(f"Шаг {self.current_index + 1} из {len(self.steps)}")
        if self.current_index + 1 < len(self.steps):
            self.next_step_label.setText(f"Дальше: {self.steps[self.current_index + 1]}")
        else:
            if self.mode == "manual":
                self.next_step_label.setText("🎉 Последний шаг! Жми «Дальше» для завершения")
            else:
                self.next_step_label.setText("🎉 Это последний шаг!")
    def _run_rehearsal(self):
        time.sleep(1.0)
        self.companion.speak_with_pause(self.companion.reh_line1(), "caring")
        self.companion.voice.prepare(self.companion.reh_line2(), self.companion.rate_pct, "caring")
        self.companion.speak_with_pause(self.companion.reh_line2(), "caring")
        for i, step in enumerate(self.steps):
            if not self.is_running:
                return
            self.current_index = i
            self._ui_step.emit()
            if i + 1 < len(self.steps):
                self.companion.voice.prepare(self.companion.reh_step(i + 1, self.steps[i + 1]),
                                             self.companion.rate_pct, "caring")
            self.companion.speak_with_pause(self.companion.reh_step(i + 1, step), "caring")
            time.sleep(0.3)
        if not self.is_running:
            return
        self.companion.speak_with_pause(self.companion.reh_end(), "excited")
        self.rehearsal_completed.emit()
        time.sleep(1.0)
        self._request_finish.emit()
    def _next_step(self):
        if self.mode != "manual":
            return
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self._show_current()
        else:
            self.btn_next.setEnabled(False)
            self.rehearsal_completed.emit()
            self._finish_safe()
    def _stop(self):
        self.is_running = False
        self.companion.voice.clear()
        self._finish_safe()
    def _finish_safe(self):
        if not self._done:
            self._done = True
            self.is_running = False
            self.finished.emit()

# ============================================
# ИГРОВОЕ ОКНО
# ============================================
class GamePage(QWidget):
    def __init__(self, gamification, battle, quests, companion, parent=None):
        super().__init__()
        self.g = gamification
        self.battle = battle
        self.quests = quests
        self.companion = companion
        self._init_ui()
    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 20, 30, 20)
        outer.setSpacing(15)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        title = QLabel("🎮 Игровой мир")
        title.setStyleSheet("font-size: 26px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        battle_frame = QFrame()
        bf = QVBoxLayout(battle_frame)
        bt = QLabel("⚔️ Текущий бой")
        bt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        bf.addWidget(bt)
        self.enemy_label = QLabel("")
        self.enemy_label.setStyleSheet("font-size: 22px; font-weight: bold; background: transparent;")
        bf.addWidget(self.enemy_label)
        self.enemy_desc = QLabel("")
        self.enemy_desc.setStyleSheet("color: #888; font-size: 13px; background: transparent;")
        self.enemy_desc.setWordWrap(True)
        bf.addWidget(self.enemy_desc)
        self.hp_bar = QProgressBar()
        bf.addWidget(self.hp_bar)
        self.hp_label = QLabel("")
        self.hp_label.setStyleSheet("color: #e74c3c; font-weight: bold; background: transparent;")
        bf.addWidget(self.hp_label)
        self.kills_label = QLabel("")
        self.kills_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        bf.addWidget(self.kills_label)
        hint = QLabel("Урон врагу: ✅ задача = 100 | 🎭 репетиция = 50 | 📁 создание = 30")
        hint.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        hint.setWordWrap(True)
        bf.addWidget(hint)
        layout.addWidget(battle_frame)
        quest_frame = QFrame()
        qf = QVBoxLayout(quest_frame)
        qt = QLabel("🎯 Ежедневные ивенты")
        qt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        qf.addWidget(qt)
        self.quest_labels = []
        for _ in range(3):
            ql = QLabel("")
            ql.setStyleSheet("font-size: 14px; background: transparent;")
            ql.setWordWrap(True)
            qf.addWidget(ql)
            self.quest_labels.append(ql)
        self.quest_reset = QLabel("Обновляются каждый день")
        self.quest_reset.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        qf.addWidget(self.quest_reset)
        layout.addWidget(quest_frame)
        eq_frame = QFrame()
        ef = QVBoxLayout(eq_frame)
        et = QLabel("🎒 Экипировка")
        et.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        ef.addWidget(et)
        self.eq_list = QListWidget()
        self.eq_list.setMaximumHeight(160)
        ef.addWidget(self.eq_list)
        self.bonus_label = QLabel("")
        self.bonus_label.setStyleSheet("color: #533483; font-weight: bold; background: transparent;")
        ef.addWidget(self.bonus_label)
        layout.addWidget(eq_frame)
        btn_ach = QPushButton("🏆 Открыть достижения")
        btn_ach.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_ach.clicked.connect(self._show_achievements)
        layout.addWidget(btn_ach)
        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)
    def refresh(self):
        emoji, name, max_hp, desc = self.battle.current()
        hp = self.battle.hp()
        self.enemy_label.setText(f"{emoji} {name}")
        self.enemy_desc.setText(desc)
        self.hp_bar.setRange(0, max_hp)
        self.hp_bar.setValue(hp)
        self.hp_label.setText(f"❤️ HP: {hp}/{max_hp}")
        self.kills_label.setText(f"⚔️ Побеждено врагов: {self.battle.kills()}")
        rows = self.quests.rows()
        for lbl, (done, desc, prog, target, reward) in zip(self.quest_labels, rows):
            mark = "✅" if done else "⬜"
            lbl.setText(f"{mark} {desc} — {prog}/{target}  (+{reward} XP)")
        self.eq_list.clear()
        for lvl, name in EQUIPMENT:
            if self.g.data["level"] >= lvl:
                self.eq_list.addItem(f"✅ {name} — активна (+5% XP)")
            else:
                self.eq_list.addItem(f"🔒 {name} — нужен уровень {lvl}")
        mult = self.g.xp_multiplier()
        self.bonus_label.setText(f"✨ Общий бонус экипировки: +{int((mult - 1) * 100)}% XP")
    def _show_achievements(self):
        dlg = AchievementsDialog(self.g, self)
        dlg.exec()

# ============================================
# ДИАЛОГ ДОСТИЖЕНИЙ
# ============================================
class AchievementsDialog(QDialog):
    def __init__(self, gamification, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏆 Достижения")
        self.setGeometry(300, 150, 500, 450)
        self.setStyleSheet(STYLESHEET)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        g = gamification.data
        stats = QLabel(f"⚔️ Уровень: {g['level']}   ✨ XP: {g['xp']}   🔥 Стрик: {g.get('streak', 0)} дн.   🐾 Послушаний: {g.get('obey_count', 0)}")
        stats.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent;")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats.setWordWrap(True)
        layout.addWidget(stats)
        ach_list = QListWidget()
        for key, (name, desc) in ACHIEVEMENTS.items():
            if key in g["achievements"]:
                ach_list.addItem(f"✅ {name} — {desc}")
            else:
                ach_list.addItem(f"🔒 {name} — {desc}")
        layout.addWidget(ach_list)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

# ============================================
# ГЛАВНОЕ ОКНО
# ============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = DataManager()
        self.gamification = Gamification(self.data.data_dir)
        self.bank = PhraseBank(self.data.data_dir)
        self.battle = BattleManager(self.gamification)
        self.quests = DailyQuests(self.gamification)
        self.avatar = AvatarManager(self.data.data_dir)
        self.voice_engine = VoiceEngine(self.data.data_dir)
        self.companion = Companion(self.voice_engine, self.bank)
        self.monitor = ActivityMonitor(self.data.data_dir, self.bank)
        self.toasts = []
        self._last_emotion = "neutral"
        self.setWindowTitle("Кай")
        self.setGeometry(150, 100, 950, 750)
        self.setStyleSheet(STYLESHEET)
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.nav = NavBar()
        self.nav.tab_changed.connect(self._on_tab)
        self.nav.minimize_requested.connect(self._minimize_to_tray)
        main_layout.addWidget(self.nav)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        main_layout.addWidget(self._create_status_bar())
        self.setCentralWidget(central)
        self.projects_page = ProjectsPage(self.data)
        self.project_page = ProjectPage(self.data, self.companion)
        self.task_page = TaskPage(self.data, self.companion)
        self.rehearsal_page = RehearsalPage(self.companion)
        self.game_page = GamePage(self.gamification, self.battle, self.quests, self.companion)
        self.settings_page = SettingsPage(self.monitor, self.voice_engine,
                                            self.avatar, self.companion, self.bank)
        self.stack.addWidget(self.projects_page)   # 0
        self.stack.addWidget(self.project_page)    # 1
        self.stack.addWidget(self.task_page)       # 2
        self.stack.addWidget(self.rehearsal_page)  # 3
        self.stack.addWidget(self.game_page)       # 4
        self.stack.addWidget(self.settings_page)   # 5
        self.stack.currentChanged.connect(self._on_stack_changed)
        self.projects_page.project_selected.connect(self._open_project)
        self.project_page.back_requested.connect(self._back_to_projects)
        self.project_page.task_selected.connect(self._open_task)
        self.task_page.back_requested.connect(self._back_to_project)
        self.task_page.start_rehearsal.connect(self._start_rehearsal)
        self.rehearsal_page.finished.connect(self._back_to_task)
        self.projects_page.project_created.connect(self._on_project_created)
        self.project_page.task_created.connect(self._on_task_created)
        self.task_page.task_done_toggled.connect(self._on_task_done_toggled)
        self.rehearsal_page.rehearsal_completed.connect(self._on_rehearsal_done)
        self.projects_page.project_deleted.connect(self.companion.on_deleted)
        self.projects_page.project_renamed.connect(self.companion.on_renamed)
        self.project_page.task_deleted.connect(self.companion.on_deleted)
        self.project_page.task_renamed.connect(self.companion.on_renamed)
        self.task_page.steps_updated.connect(self.companion.on_steps_updated)
        self.monitor.alert.connect(self._on_monitor_alert)
        self.monitor.work_block.connect(self._on_work_block)
        self.monitor.context.connect(self._on_context)
        self.monitor.reward.connect(self._award)
        self.monitor.obeyed.connect(self._on_obeyed)
        self.settings_page.avatar_changed.connect(
            lambda: self._show_message(self._last_emotion, self.companion_text.text()))
        self.companion.message.connect(self._show_message)
        self._create_tray()
        self._update_xp_ui()
        QTimer.singleShot(500, self.companion.greet)
        self.projects_page.refresh()
    def _make_icon(self):
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#533483"))
        p.drawRoundedRect(2, 2, 60, 60, 14, 14)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI Emoji", 28))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "😏")
        p.end()
        return QIcon(pix)
    def _create_tray(self):
        self.tray = QSystemTrayIcon(self._make_icon(), self)
        menu = QMenu()
        act_show = menu.addAction("📂 Открыть окно")
        act_show.triggered.connect(self._show_window)
        self.act_monitor = menu.addAction("👁 Мониторинг активности")
        self.act_monitor.setCheckable(True)
        self.act_monitor.setChecked(self.monitor.enabled)
        self.act_monitor.toggled.connect(self._tray_monitor_toggled)
        act_settings = menu.addAction("⚙ Настройки")
        act_settings.triggered.connect(self._open_settings)
        menu.addSeparator()
        act_quit = menu.addAction("❌ Выход")
        act_quit.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
    def _tray_monitor_toggled(self, on):
        self.monitor.set_enabled(on)
    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
    def _minimize_to_tray(self):
        self.hide()
        push_notify("Кай", self.bank.say("minimize"))
    def _open_settings(self):
        self._show_window()
        self.stack.setCurrentIndex(5)
    def _quit(self):
        self.tray.hide()
        QApplication.quit()
    def closeEvent(self, event):
        self.tray.hide()
        QApplication.quit()
    def _on_obeyed(self):
        if self.gamification.add_obey():
            self._unlock("obedient")
    def _on_context(self, cat, title):
        t = title[:60]
        if cat == "off":
            self.context_label.setText("👁 мониторинг выключен")
        elif cat == "distract":
            site = self.monitor._detect_distract(title.lower()) or "сайт"
            self.context_label.setText(f"👁 {site}: {t}")
        elif cat == "work":
            app = self.monitor._detect_app(title.lower()) or "работа"
            self.context_label.setText(f"👁 {app}: {t}")
        elif cat == "browse":
            self.context_label.setText(f"👁 браузер: {t}")
        elif cat == "self":
            self.context_label.setText("👁 Кай")
        else:
            self.context_label.setText(f"👁 {t or '—'}")
    def _on_monitor_alert(self, emotion, text):
        if self.monitor.voice_enabled:
            self.companion.say_aloud(emotion, text)
        else:
            self.companion.say(emotion, text)
        self._toast("Кай", text)
        if self.monitor.push_enabled:
            push_notify("Кай", text)
    def _on_work_block(self, minutes):
        self.companion.on_work_block(minutes)
        self._award(20)
        self._toast("Кай", f"Фокус-блок {minutes} минут! +20 XP")
        if self.monitor.push_enabled:
            push_notify("Кай", f"{minutes} минут непрерывной работы! +20 XP")
    def _on_tab(self, name):
        if name == "tasks":
            self.stack.setCurrentIndex(0)
        elif name == "game":
            self.stack.setCurrentIndex(4)
        else:
            self.stack.setCurrentIndex(5)
        self.nav.set_active(name)
    def _on_stack_changed(self, idx):
        if idx == 4:
            self.game_page.refresh()
            self.nav.set_active("game")
        elif idx == 5:
            self.settings_page.sync()
            self.nav.set_active("settings")
        else:
            self.nav.set_active("tasks")
    def _create_status_bar(self):
        status = QWidget()
        status.setFixedHeight(60)
        status.setStyleSheet("background-color: #16213e; border-top: 2px solid #0f3460;")
        layout = QHBoxLayout(status)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setSpacing(12)
        self.companion_avatar = QLabel("😏")
        self.companion_avatar.setFixedSize(46, 46)
        self.companion_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.companion_avatar.setStyleSheet("font-size: 30px; background: transparent;")
        layout.addWidget(self.companion_avatar)
        self.companion_text = QLabel("Привет~ Я Кай.")
        self.companion_text.setStyleSheet("font-size: 13px; color: #eaeaea; background: transparent;")
        self.companion_text.setWordWrap(True)
        layout.addWidget(self.companion_text, 1)
        self.context_label = QLabel("👁 —")
        self.context_label.setStyleSheet("font-size: 11px; color: #888; background: transparent;")
        self.context_label.setMaximumWidth(320)
        layout.addWidget(self.context_label)
        self.level_label = QLabel("⚔️ Ур. 1")
        self.level_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #533483; background: transparent;")
        layout.addWidget(self.level_label)
        self.xp_bar = QProgressBar()
        self.xp_bar.setFixedWidth(120)
        self.xp_bar.setRange(0, 100)
        layout.addWidget(self.xp_bar)
        self.xp_label = QLabel("✨ 0/100")
        self.xp_label.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        layout.addWidget(self.xp_label)
        return status
    def _show_message(self, emotion, text):
        self._last_emotion = emotion
        pix = self.avatar.pixmap_for(emotion, 46)
        if pix:
            self.companion_avatar.setPixmap(pix)
        else:
            self.companion_avatar.clear()
            emojis = {"happy": "😊", "neutral": "😏", "worried": "🥺",
                      "sarcastic": "😈", "excited": "🤩", "caring": "💜"}
            self.companion_avatar.setText(emojis.get(emotion, "😏"))
        self.companion_text.setText(text)
    def _update_xp_ui(self):
        g = self.gamification
        self.level_label.setText(f"⚔️ Ур. {g.data['level']}")
        self.xp_bar.setValue(g.progress_percent())
        self.xp_label.setText(f"✨ {g.data['xp']}/{g.next_level_xp()}")
    def _toast(self, title, text):
        toast = Toast(title, text)
        toast.closed.connect(self._remove_toast)
        screen = QApplication.primaryScreen().availableGeometry()
        y = 60 + 90 * len(self.toasts)
        toast.move(screen.right() - 340, y)
        self.toasts.append(toast)
        toast.show()
    def _remove_toast(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
    def _unlock(self, key):
        if self.gamification.unlock(key):
            name, desc = ACHIEVEMENTS[key]
            self._toast("Кай", f"🏆 Достижение: {name}")
            self.companion.say_aloud("excited", self.bank.say("achievement", name=name))
    def _award(self, amount):
        amount = int(amount * self.gamification.xp_multiplier())
        gained, leveled, level = self.gamification.add_xp(amount)
        self._update_xp_ui()
        if leveled:
            self.companion.on_level_up(level)
            if level >= 5:
                self._unlock("level_5")
        return gained
    def _hit_enemy(self, amount, source):
        emoji, name, max_hp, desc = self.battle.current()
        defeated = self.battle.damage(amount)
        if defeated:
            self.companion.on_enemy_defeated(name)
            self._award(150)
            self._unlock("dragon_slayer")
            if self.battle.kills() >= 5:
                self._unlock("hunter5")
        else:
            self.companion.on_enemy_hit(name, amount, self.battle.hp())
        self.game_page.refresh()
    def _quest_progress(self, key):
        reward = self.quests.progress(key)
        if reward:
            self._award(reward)
            self.companion.on_quest_done(reward)
        self.game_page.refresh()
    def _on_project_created(self, name):
        self._award(20)
        self.companion.on_project_created(name)
        self._unlock("first_project")
        self._hit_enemy(30, "проект")
        self._quest_progress("create1")
    def _on_task_created(self, name):
        self._award(15)
        self.companion.on_task_created(name)
        self._unlock("first_task")
        self._hit_enemy(30, "задача")
        self._quest_progress("create1")
    def _on_rehearsal_done(self):
        self._award(25)
        self.gamification.data["rehearsals"] = self.gamification.data.get("rehearsals", 0) + 1
        self.gamification._save()
        self.companion.on_rehearsal_done()
        self._unlock("first_rehearsal")
        self._hit_enemy(50, "репетиция")
        self._quest_progress("reh1")
    def _on_task_done_toggled(self, now_done, name):
        if now_done:
            self._award(100)
            self.gamification.data["tasks_done"] = self.gamification.data.get("tasks_done", 0) + 1
            self.gamification._save()
            self.companion.on_task_done(name)
            self._unlock("first_done")
            if self.gamification.data["tasks_done"] >= 10:
                self._unlock("ten_tasks")
            if self.gamification.update_streak():
                self._unlock("streak_3")
            pid = self.task_page.current_project_id
            p = self.data.get_project(pid)
            if p and p["tasks"] and all(t["done"] for t in p["tasks"]):
                self._unlock("all_done")
            self._hit_enemy(100, "задача")
            self._quest_progress("tasks2")
        else:
            self.companion.on_task_undone()
    def _open_project(self, project_id):
        self.project_page.load_project(project_id)
        self.stack.setCurrentIndex(1)
    def _back_to_projects(self):
        self.projects_page.refresh()
        self.stack.setCurrentIndex(0)
    def _open_task(self, project_id, task_id):
        self.task_page.load_task(project_id, task_id)
        self.stack.setCurrentIndex(2)
    def _back_to_project(self):
        self.project_page.refresh()
        self.stack.setCurrentIndex(1)
    def _start_rehearsal(self, steps, task_name, mode):
        self.companion.on_rehearsal_start(task_name, mode)
        self.rehearsal_page.start(steps, task_name, mode)
        self.stack.setCurrentIndex(3)
    def _back_to_task(self):
        self.stack.setCurrentIndex(2)

# ============================================
# ЗАПУСК
# ============================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Kai")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())