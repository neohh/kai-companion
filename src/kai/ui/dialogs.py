"""
ui.dialogs — диалоговые окна.
Владельцы: StepsDialog.
Зависимости: PyQt6 (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
QLineEdit, QPushButton); kai.ui.theme.STYLESHEET.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QScrollArea, QWidget, QLineEdit, QPushButton)

from kai.ui.theme import STYLESHEET


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
