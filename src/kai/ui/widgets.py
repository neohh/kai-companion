"""
ui.widgets — мелкие переиспользуемые виджеты.
Владельцы: Toast.
Зависимости: PyQt6 (QWidget, QVBoxLayout, QFrame, QLabel, QTimer, Qt, pyqtSignal).
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFrame, QLabel)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


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
        self._timeout_ms = 5000
        QTimer.singleShot(self._timeout_ms, self.close)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)
