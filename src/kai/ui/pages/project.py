"""
ui.pages.project — экран проекта (список задач).
Владельцы: ProjectPage.
Зависимости: PyQt6; kai.core.storage.DataManager; kai.core.companion.Companion;
kai.ui.dialogs.StepsDialog.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal

from kai.ui.dialogs import StepsDialog


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
