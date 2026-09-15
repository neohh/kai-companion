"""
ui.nav — верхняя панель навигации.
Владельцы: NavBar (сигналы tab_changed, minimize_requested).
Зависимости: PyQt6 (QWidget, QHBoxLayout, QPushButton, pyqtSignal).
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal


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
