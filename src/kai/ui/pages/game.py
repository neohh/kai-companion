"""
ui.pages.game — игровой экран: бой, ивенты, экипировка + диалог достижений.
Владельцы: GamePage, AchievementsDialog.
Зависимости: PyQt6; kai.constants (EQUIPMENT, ACHIEVEMENTS); kai.ui.theme.STYLESHEET.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, QFrame,
                             QProgressBar, QListWidget, QScrollArea, QDialog)
from PyQt6.QtCore import Qt

from kai.constants import EQUIPMENT, ACHIEVEMENTS
from kai.ui.theme import STYLESHEET


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
