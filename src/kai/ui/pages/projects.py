"""
ui.pages.projects — экран списка проектов.
Владельцы: ProjectsPage.
Зависимости: PyQt6; kai.core.storage.DataManager.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QListWidgetItem, QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal


# ============================================
# ЭКРАН ПРОЕКТОВ
# ============================================
class ProjectsPage(QWidget):
    project_selected = pyqtSignal(int)
    project_created = pyqtSignal(str)
    project_deleted = pyqtSignal()
    project_renamed = pyqtSignal()

    def __init__(self, data_manager):
        super().__init__()
        self.data = data_manager
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        title = QLabel("🎯 Мои проекты")
        title.setStyleSheet("font-size: 28px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.btn_new = QPushButton("➕ Новый проект")
        self.btn_new.setStyleSheet("background-color: #533483; font-size: 16px; font-weight: bold; padding: 15px;")
        self.btn_new.clicked.connect(self._create_project)
        layout.addWidget(self.btn_new)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_project)
        layout.addWidget(self.list)
        edit_layout = QHBoxLayout()
        btn_rename = QPushButton("✏️ Переименовать")
        btn_rename.clicked.connect(self._rename_project)
        edit_layout.addWidget(btn_rename)
        btn_delete = QPushButton("🗑 Удалить")
        btn_delete.clicked.connect(self._delete_project)
        edit_layout.addWidget(btn_delete)
        layout.addLayout(edit_layout)
        hint = QLabel("💡 Двойной клик по проекту → открыть")
        hint.setStyleSheet("color: #666; font-size: 12px; background: transparent;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def refresh(self):
        self.list.clear()
        for project in self.data.get_projects():
            done = sum(1 for t in project["tasks"] if t["done"])
            total = len(project["tasks"])
            item = QListWidgetItem(f"📁 {project['name']}  ({done}/{total})")
            item.setData(Qt.ItemDataRole.UserRole, project["id"])
            self.list.addItem(item)

    def _selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _create_project(self):
        name, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if ok and name.strip():
            self.data.create_project(name.strip())
            self.refresh()
            self.project_created.emit(name.strip())

    def _rename_project(self):
        pid = self._selected_id()
        if pid is None:
            return
        p = self.data.get_project(pid)
        name, ok = QInputDialog.getText(self, "Переименовать", "Новое название:", text=p["name"])
        if ok and name.strip():
            self.data.rename_project(pid, name.strip())
            self.refresh()
            self.project_renamed.emit()

    def _delete_project(self):
        pid = self._selected_id()
        if pid is None:
            return
        p = self.data.get_project(pid)
        reply = QMessageBox.question(self, "Удалить проект",
                                     f"Удалить проект '{p['name']}' со всеми задачами?")
        if reply == QMessageBox.StandardButton.Yes:
            self.data.delete_project(pid)
            self.refresh()
            self.project_deleted.emit()

    def _open_project(self, item):
        self.project_selected.emit(item.data(Qt.ItemDataRole.UserRole))
