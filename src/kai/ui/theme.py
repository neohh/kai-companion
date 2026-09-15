"""
ui.theme — единый источник стилей приложения.
Владельцы: STYLESHEET.
Зависимости: нет.
"""

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
