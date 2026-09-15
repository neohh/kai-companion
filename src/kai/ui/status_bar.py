"""
ui.status_bar — нижняя панель Кая: аватар, реплика, контекст, XP,
шкала близости/настроения (Mood) и лента актуальных желаний (desire strip).
Владельцы: StatusBar (выделен из монолитного метода _create_status_bar).
Зависимости: PyQt6 (QWidget, QHBoxLayout/QVBoxLayout, QLabel, QProgressBar, QFrame).
Часть B: индикатор близости и статуса настроения (Mood).
Desire strip: постоянное место под актуальное предложение Кая — текст, который
он говорит, и кнопки-действия («пройти репетицию», «открыть задачи», «позже»).
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QProgressBar, QFrame, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal

MOOD_STATUS_RU = {
    "warm": "тёплый",
    "neutral": "нейтральный",
    "cold": "холодный",
    "boycott": "молчит",
}

MOOD_BAR_COLOR = {
    "warm": "#7c4dff",
    "neutral": "#0f3460",
    "cold": "#37474f",
    "boycott": "#263238",
}


class StatusBar(QWidget):
    """Нижняя панель: создаёт виджеты-поля, которыми управляет MainWindow."""

    desire_action = pyqtSignal(str)  # id нажатой кнопки желания

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(116)
        self.setStyleSheet("background-color: #16213e; border-top: 2px solid #0f3460;")
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(14)

        # --- аватар ---
        self.companion_avatar = QLabel("😏")
        self.companion_avatar.setFixedSize(76, 76)
        self.companion_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.companion_avatar.setStyleSheet(
            "font-size: 50px; background: #0f3460; border: 2px solid #533483;"
            " border-radius: 38px;")
        root.addWidget(self.companion_avatar, 0, Qt.AlignmentFlag.AlignVCenter)

        # --- реплика + контекст ---
        speech = QVBoxLayout()
        speech.setSpacing(2)
        self.companion_text = QLabel("Привет~ Я Кай.")
        self.companion_text.setStyleSheet(
            "font-size: 14px; color: #eaeaea; background: transparent;")
        self.companion_text.setWordWrap(True)
        speech.addWidget(self.companion_text, 1)
        self.context_label = QLabel("👁 —")
        self.context_label.setStyleSheet(
            "font-size: 11px; color: #888; background: transparent;")
        self.context_label.setMaximumWidth(360)
        speech.addWidget(self.context_label)
        root.addLayout(speech, 3)

        # --- лента желаний: постоянное место под актуальное предложение ---
        self.desire_frame = QFrame()
        self.desire_frame.setStyleSheet(
            "QFrame { background-color: #0f3460; border: 1px solid #533483;"
            " border-radius: 8px; }"
            "QLabel { background: transparent; }")
        dv = QVBoxLayout(self.desire_frame)
        dv.setContentsMargins(10, 5, 10, 6)
        dv.setSpacing(3)
        self.desire_title = QLabel("💭 Кай хочет:")
        self.desire_title.setStyleSheet(
            "font-size: 10px; color: #b39ddb; background: transparent;")
        dv.addWidget(self.desire_title)
        self.desire_text = QLabel("")
        self.desire_text.setWordWrap(True)
        self.desire_text.setStyleSheet(
            "font-size: 12px; color: #eaeaea; background: transparent;")
        dv.addWidget(self.desire_text, 1)
        self.desire_buttons_row = QHBoxLayout()
        self.desire_buttons_row.setSpacing(6)
        dv.addLayout(self.desire_buttons_row)
        self.desire_frame.hide()
        root.addWidget(self.desire_frame, 2)

        # --- правая колонка: уровни/XP + шкала настроения ---
        right = QVBoxLayout()
        right.setSpacing(4)
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.level_label = QLabel("⚔️ Ур. 1")
        self.level_label.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #533483; background: transparent;")
        row1.addWidget(self.level_label)
        self.xp_bar = QProgressBar()
        self.xp_bar.setFixedWidth(120)
        self.xp_bar.setRange(0, 100)
        row1.addWidget(self.xp_bar)
        self.xp_label = QLabel("✨ 0/100")
        self.xp_label.setStyleSheet(
            "font-size: 12px; color: #888; background: transparent;")
        row1.addWidget(self.xp_label)
        right.addLayout(row1)
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.mood_emoji_label = QLabel("💜")
        self.mood_emoji_label.setStyleSheet(
            "font-size: 15px; background: transparent;")
        row2.addWidget(self.mood_emoji_label)
        self.mood_bar = QProgressBar()
        self.mood_bar.setFixedWidth(110)
        self.mood_bar.setRange(0, 100)
        self.mood_bar.setValue(50)
        self.mood_bar.setFormat("%v")
        self.mood_bar.setStyleSheet("""
            QProgressBar { background-color: #1a1a2e; border: 1px solid #0f3460;
                           border-radius: 6px; text-align: center; color: #eaeaea;
                           font-size: 10px; }
            QProgressBar::chunk { background-color: #7c4dff; border-radius: 5px; }
        """)
        self.mood_bar.setToolTip("Близость Кая (0–100) и статус настроения")
        row2.addWidget(self.mood_bar)
        self.mood_status_label = QLabel("нейтральный")
        self.mood_status_label.setStyleSheet(
            "font-size: 11px; color: #888; background: transparent;")
        row2.addWidget(self.mood_status_label)
        right.addLayout(row2)
        root.addLayout(right, 0)

    # --- mood ---
    def set_mood(self, closeness, status, emoji, extra=""):
        """Обновить шкалу настроения: близость 0..100, статус, эмодзи."""
        self.mood_bar.setValue(int(max(0, min(100, closeness))))
        color = MOOD_BAR_COLOR.get(status, "#0f3460")
        self.mood_bar.setStyleSheet("""
            QProgressBar { background-color: #1a1a2e; border: 1px solid #0f3460;
                           border-radius: 6px; text-align: center; color: #eaeaea;
                           font-size: 10px; }
            QProgressBar::chunk { background-color: %s; border-radius: 5px; }
        """ % color)
        self.mood_emoji_label.setText(emoji)
        text = MOOD_STATUS_RU.get(status, status)
        if extra:
            text = f"{text} {extra}"
        self.mood_status_label.setText(text)

    # --- desire strip ---
    def set_desire(self, text, actions):
        """Показать актуальное желание Кая. actions: list[(id, label)]."""
        while self.desire_buttons_row.count():
            item = self.desire_buttons_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for cid, label in actions:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #16213e; color: #ffffff;
                    border: 1px solid #b39ddb; border-radius: 6px;
                    padding: 4px 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #533483; }
            """)
            b.clicked.connect(lambda _, c=cid: self.desire_action.emit(c))
            self.desire_buttons_row.addWidget(b)
        self.desire_text.setText(text)
        self.desire_frame.show()

    def clear_desire(self):
        self.desire_frame.hide()
