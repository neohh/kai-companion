"""
ui.status_bar — нижняя панель статуса (аватар, реплика, контекст, XP).
Владельцы: StatusBar (выделен из монолитного метода _create_status_bar).
Зависимости: PyQt6 (QWidget, QHBoxLayout, QLabel, QProgressBar).
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt


class StatusBar(QWidget):
    """Нижняя панель: создаёт виджеты-поля, которыми управляет MainWindow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setStyleSheet("background-color: #16213e; border-top: 2px solid #0f3460;")
        layout = QHBoxLayout(self)
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
