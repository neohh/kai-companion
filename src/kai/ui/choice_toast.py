"""
ui.choice_toast — тост-выбор с 2-3 кнопками («Выйти сейчас» / «+5 мин в долг» / «Игнорирую»).
Владельцы: ChoiceToast (сигнал answered: choice_id).
Зависимости: PyQt6; наследует поведение ui.widgets.Toast (таймаут, поверх окон).
Ответ уходит сигналом в monitor/relationship; «Игнор» = on_ignored.
"""
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from kai.ui.widgets import Toast


class ChoiceToast(Toast):
    """Тост с кнопками выбора; закрытие без ответа трактуется как игнор."""

    answered = pyqtSignal(object, str)  # (toast, choice_id)

    def __init__(self, title, text, choices, choice_id=""):
        # choices: list[(id, label)] — 2-3 штуки; choice_id — идентификатор события
        Toast.__init__(self, title, text)
        self.choice_id = choice_id
        self._answered = False
        layout = self.layout()
        frame = layout.itemAt(0).widget()
        fl = frame.layout()
        row = QHBoxLayout()
        row.setSpacing(6)
        for cid, label in choices:
            b = QPushButton(label)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background-color: #0f3460; color: #ffffff;
                    border: 1px solid #eaeaea; border-radius: 6px;
                    padding: 5px 8px; font-size: 11px;
                }
                QPushButton:hover { background-color: #533483; }
            """)
            b.clicked.connect(lambda _, c=cid: self._choose(c))
            row.addWidget(b)
        fl.addLayout(row)

    def _choose(self, cid):
        self._answered = True
        self.answered.emit(self, cid)
        self.close()

    def closeEvent(self, event):
        if not self._answered:
            # закрытие по таймауту/крестом = игрок проигнорировал Кая
            self.answered.emit(self, "ignore")
        super().closeEvent(event)
