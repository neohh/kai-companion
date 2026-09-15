"""
ui.pages.task — экран задачи: шаги, отметка выполнения, скорость озвучки.
Владельцы: TaskPage.
Зависимости: PyQt6; kai.core.storage.DataManager; kai.core.companion.Companion;
kai.ui.dialogs.StepsDialog.
"""
import threading

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QListWidget, QFrame, QSlider, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal

from kai.ui.dialogs import StepsDialog


# ============================================
# ЭКРАН ЗАДАЧИ
# ============================================
class TaskPage(QWidget):
    back_requested = pyqtSignal()
    start_rehearsal = pyqtSignal(list, str, str)
    task_done_toggled = pyqtSignal(bool, str)
    steps_updated = pyqtSignal()

    def __init__(self, data_manager, companion):
        super().__init__()
        self.data = data_manager
        self.companion = companion
        self.current_project_id = None
        self.current_task_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        btn_back = QPushButton("← Назад к проекту")
        btn_back.clicked.connect(self.back_requested.emit)
        layout.addWidget(btn_back)
        self.title = QLabel("📝 Задача")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        steps_frame = QFrame()
        steps_layout = QVBoxLayout(steps_frame)
        steps_label = QLabel("👣 Шаги:")
        steps_label.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        steps_layout.addWidget(steps_label)
        self.steps_list = QListWidget()
        steps_layout.addWidget(self.steps_list)
        btn_steps = QPushButton("✏️ Редактировать шаги")
        btn_steps.clicked.connect(self._edit_steps)
        steps_layout.addWidget(btn_steps)
        layout.addWidget(steps_frame)
        btn_layout = QHBoxLayout()
        self.btn_done = QPushButton("⬜ Отметить выполненным")
        self.btn_done.clicked.connect(self._toggle_done)
        btn_layout.addWidget(self.btn_done)
        layout.addLayout(btn_layout)
        reh_layout = QHBoxLayout()
        btn_reh_voice = QPushButton("🎙 Репетиция с озвучкой")
        btn_reh_voice.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_reh_voice.clicked.connect(lambda: self._start_rehearsal("voice"))
        reh_layout.addWidget(btn_reh_voice)
        btn_reh_manual = QPushButton("🖐 Репетиция вручную")
        btn_reh_manual.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_reh_manual.clicked.connect(lambda: self._start_rehearsal("manual"))
        reh_layout.addWidget(btn_reh_manual)
        layout.addLayout(reh_layout)
        speed_frame = QFrame()
        speed_layout = QVBoxLayout(speed_frame)
        speed_title = QLabel("⚡ Скорость озвучки и пауз")
        speed_title.setStyleSheet("font-size: 14px; font-weight: bold; background: transparent;")
        speed_layout.addWidget(speed_title)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(5, 25)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self._on_speed_change)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        speed_layout.addWidget(self.speed_label)
        self._on_speed_change(10)
        layout.addWidget(speed_frame)

    def load_task(self, project_id, task_id):
        self.current_project_id = project_id
        self.current_task_id = task_id
        self._refresh()

    def _refresh(self):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if not task:
            return
        self.title.setText(f"📝 {task['name']}")
        self.steps_list.clear()
        for i, step in enumerate(task["steps"], 1):
            self.steps_list.addItem(f"{i}. {step}")
        self.btn_done.setText("✅ Снять отметку" if task["done"] else "⬜ Отметить выполненным")

    def _edit_steps(self):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if not task:
            return
        dlg = StepsDialog(self, initial=task["steps"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            steps = dlg.get_steps()
            if steps:
                self.data.update_task_steps(self.current_project_id, self.current_task_id, steps)
                self._refresh()
                self.steps_updated.emit()
            else:
                self.companion.on_empty_steps()

    def _toggle_done(self):
        now_done = self.data.toggle_task_done(self.current_project_id, self.current_task_id)
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        self._refresh()
        self.task_done_toggled.emit(now_done, task["name"] if task else "")

    def _on_speed_change(self, value):
        self.companion.set_speed_value(value)
        rate = 50 - 2 * value
        pause_per_100 = value * 0.002 * 100
        if value <= 8:
            tempo = "Очень быстро"
        elif value <= 15:
            tempo = "Средне"
        else:
            tempo = "Спокойно"
        self.speed_label.setText(f"{tempo}: голос +{rate}%, пауза {pause_per_100:.0f} сек на 100 символов")

    def _start_rehearsal(self, mode):
        task = self.data.get_task(self.current_project_id, self.current_task_id)
        if task and task["steps"]:
            self.start_rehearsal.emit(task["steps"], task["name"], mode)
