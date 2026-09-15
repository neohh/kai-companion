"""
ui.pages.rehearsal — экран репетиции задачи (голосовой и ручной режимы).
Владельцы: RehearsalPage.
Зависимости: time, threading; PyQt6; kai.core.companion.Companion.
"""
import time
import threading

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal


# ============================================
# ЭКРАН РЕПЕТИЦИИ
# ============================================
class RehearsalPage(QWidget):
    finished = pyqtSignal()
    rehearsal_completed = pyqtSignal()
    _ui_step = pyqtSignal()
    _request_finish = pyqtSignal()

    def __init__(self, companion):
        super().__init__()
        self.companion = companion
        self.steps = []
        self.current_index = 0
        self.mode = "voice"
        self.is_running = False
        self._done = True
        self._ui_step.connect(self._show_current)
        self._request_finish.connect(self._finish_safe)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(50, 40, 50, 40)
        title = QLabel("🎭 РЕПЕТИЦИЯ")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #533483; background: transparent; letter-spacing: 5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addSpacing(10)
        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("font-size: 13px; color: #888; background: transparent;")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mode_label)
        layout.addSpacing(10)
        self.task_name = QLabel("")
        self.task_name.setStyleSheet("font-size: 16px; color: #888; background: transparent;")
        self.task_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.task_name)
        layout.addStretch()
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("font-size: 14px; color: #666; background: transparent;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        layout.addSpacing(20)
        self.current_step = QLabel("...")
        self.current_step.setStyleSheet("font-size: 36px; font-weight: bold; color: #eaeaea; background: transparent; padding: 30px;")
        self.current_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_step.setWordWrap(True)
        self.current_step.setMinimumHeight(180)
        layout.addWidget(self.current_step)
        layout.addSpacing(20)
        self.next_step_label = QLabel("")
        self.next_step_label.setStyleSheet("font-size: 16px; color: #666; background: transparent; font-style: italic;")
        self.next_step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_step_label.setWordWrap(True)
        layout.addWidget(self.next_step_label)
        layout.addStretch()
        btn_layout = QHBoxLayout()
        self.btn_stop = QPushButton("⏹ Остановить")
        self.btn_stop.clicked.connect(self._stop)
        btn_layout.addWidget(self.btn_stop)
        self.btn_next = QPushButton("Дальше →")
        self.btn_next.setStyleSheet("background-color: #533483; font-weight: bold; padding: 15px 30px;")
        self.btn_next.clicked.connect(self._next_step)
        btn_layout.addWidget(self.btn_next)
        layout.addLayout(btn_layout)

    def start(self, steps, task_name, mode):
        self.steps = steps
        self.mode = mode
        self.task_name.setText(f"📝 {task_name}")
        self.current_index = 0
        self.is_running = True
        self._done = False
        if mode == "voice":
            self.mode_label.setText("🎙 Авто-режим: Кай ведёт, листание отключено")
            self.btn_next.setEnabled(False)
            self.btn_stop.setText("⏹ Остановить")
            # предзагрузка первых реплик
            self.companion.voice.prepare(self.companion.reh_line1(), self.companion.rate_pct, "caring")
            threading.Thread(target=self._run_rehearsal, daemon=True).start()
        else:
            self.mode_label.setText("🖐 Ручной режим: листай сам, Кай молчит")
            self.btn_next.setEnabled(True)
            self.btn_stop.setText("⏹ Отменить")
            self._show_current()

    def _show_current(self):
        if not self.steps or self.current_index >= len(self.steps):
            return
        self.current_step.setText(self.steps[self.current_index])
        self.progress_label.setText(f"Шаг {self.current_index + 1} из {len(self.steps)}")
        if self.current_index + 1 < len(self.steps):
            self.next_step_label.setText(f"Дальше: {self.steps[self.current_index + 1]}")
        else:
            if self.mode == "manual":
                self.next_step_label.setText("🎉 Последний шаг! Жми «Дальше» для завершения")
            else:
                self.next_step_label.setText("🎉 Это последний шаг!")

    def _run_rehearsal(self):
        time.sleep(1.0)
        self.companion.speak_with_pause(self.companion.reh_line1(), "caring")
        self.companion.voice.prepare(self.companion.reh_line2(), self.companion.rate_pct, "caring")
        self.companion.speak_with_pause(self.companion.reh_line2(), "caring")
        for i, step in enumerate(self.steps):
            if not self.is_running:
                return
            self.current_index = i
            self._ui_step.emit()
            if i + 1 < len(self.steps):
                self.companion.voice.prepare(self.companion.reh_step(i + 1, self.steps[i + 1]),
                                             self.companion.rate_pct, "caring")
            self.companion.speak_with_pause(self.companion.reh_step(i + 1, step), "caring")
            time.sleep(0.3)
        if not self.is_running:
            return
        self.companion.speak_with_pause(self.companion.reh_end(), "excited")
        self.rehearsal_completed.emit()
        time.sleep(1.0)
        self._request_finish.emit()

    def _next_step(self):
        if self.mode != "manual":
            return
        if self.current_index < len(self.steps) - 1:
            self.current_index += 1
            self._show_current()
        else:
            self.btn_next.setEnabled(False)
            self.rehearsal_completed.emit()
            self._finish_safe()

    def _stop(self):
        self.is_running = False
        self.companion.voice.clear()
        self._finish_safe()

    def _finish_safe(self):
        if not self._done:
            self._done = True
            self.is_running = False
            self.finished.emit()
