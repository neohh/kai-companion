"""
constants — игровые и системные константы приложения.
Владельцы: ACHIEVEMENTS, EQUIPMENT, ENEMIES, QUEST_DEFS, EMOTIONS_RU,
DEFAULT_DISTRACT, DISTRACT_NAMES, DEFAULT_WORK, BROWSER_KEYS, APP_NAMES.
Зависимости: нет.
"""

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
