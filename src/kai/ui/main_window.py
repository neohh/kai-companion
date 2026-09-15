"""
ui.main_window — главное окно: composition root, создание всех сервисов и связывание сигналов.
Владельцы: MainWindow.
Зависимости: PyQt6; core.* (DataManager, Gamification, BattleManager, DailyQuests,
PhraseBank, AvatarManager, ActivityMonitor, Companion); voice.engine.VoiceEngine;
ui.theme.STYLESHEET; ui.nav.NavBar; ui.status_bar.StatusBar; ui.widgets.Toast;
ui.pages.*; kai.constants.ACHIEVEMENTS; kai.sys_utils.push_notify.
"""
import sys

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QStackedWidget, QLabel, QSystemTrayIcon, QMenu)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QColor, QFont

from kai.constants import ACHIEVEMENTS
from kai.sys_utils import push_notify
from kai.core.storage import DataManager
from kai.core.gamification import Gamification, BattleManager, DailyQuests
from kai.core.phrases import PhraseBank
from kai.core.avatar import AvatarManager
from kai.core.monitor import ActivityMonitor
from kai.core.companion import Companion
from kai.voice.engine import VoiceEngine
from kai.ui.theme import STYLESHEET
from kai.ui.nav import NavBar
from kai.ui.status_bar import StatusBar
from kai.ui.widgets import Toast
from kai.ui.pages.projects import ProjectsPage
from kai.ui.pages.project import ProjectPage
from kai.ui.pages.task import TaskPage
from kai.ui.pages.rehearsal import RehearsalPage
from kai.ui.pages.game import GamePage
from kai.ui.pages.settings import SettingsPage


# ============================================
# ГЛАВНОЕ ОКНО
# ============================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = DataManager()
        self.gamification = Gamification(self.data.data_dir)
        self.bank = PhraseBank(self.data.data_dir)
        self.battle = BattleManager(self.gamification)
        self.quests = DailyQuests(self.gamification)
        self.avatar = AvatarManager(self.data.data_dir)
        self.voice_engine = VoiceEngine(self.data.data_dir)
        self.companion = Companion(self.voice_engine, self.bank)
        self.monitor = ActivityMonitor(self.data.data_dir, self.bank)
        self.toasts = []
        self._last_emotion = "neutral"
        self.setWindowTitle("Кай")
        self.setGeometry(150, 100, 950, 750)
        self.setStyleSheet(STYLESHEET)
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.nav = NavBar()
        self.nav.tab_changed.connect(self._on_tab)
        self.nav.minimize_requested.connect(self._minimize_to_tray)
        main_layout.addWidget(self.nav)
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        self.status_bar_widget = StatusBar()
        main_layout.addWidget(self.status_bar_widget)
        self.setCentralWidget(central)
        self.projects_page = ProjectsPage(self.data)
        self.project_page = ProjectPage(self.data, self.companion)
        self.task_page = TaskPage(self.data, self.companion)
        self.rehearsal_page = RehearsalPage(self.companion)
        self.game_page = GamePage(self.gamification, self.battle, self.quests, self.companion)
        self.settings_page = SettingsPage(self.monitor, self.voice_engine,
                                          self.avatar, self.companion, self.bank)
        self.stack.addWidget(self.projects_page)   # 0
        self.stack.addWidget(self.project_page)    # 1
        self.stack.addWidget(self.task_page)       # 2
        self.stack.addWidget(self.rehearsal_page)  # 3
        self.stack.addWidget(self.game_page)       # 4
        self.stack.addWidget(self.settings_page)   # 5
        self.stack.currentChanged.connect(self._on_stack_changed)
        self.projects_page.project_selected.connect(self._open_project)
        self.project_page.back_requested.connect(self._back_to_projects)
        self.project_page.task_selected.connect(self._open_task)
        self.task_page.back_requested.connect(self._back_to_project)
        self.task_page.start_rehearsal.connect(self._start_rehearsal)
        self.rehearsal_page.finished.connect(self._back_to_task)
        self.projects_page.project_created.connect(self._on_project_created)
        self.project_page.task_created.connect(self._on_task_created)
        self.task_page.task_done_toggled.connect(self._on_task_done_toggled)
        self.rehearsal_page.rehearsal_completed.connect(self._on_rehearsal_done)
        self.projects_page.project_deleted.connect(self.companion.on_deleted)
        self.projects_page.project_renamed.connect(self.companion.on_renamed)
        self.project_page.task_deleted.connect(self.companion.on_deleted)
        self.project_page.task_renamed.connect(self.companion.on_renamed)
        self.task_page.steps_updated.connect(self.companion.on_steps_updated)
        self.monitor.alert.connect(self._on_monitor_alert)
        self.monitor.work_block.connect(self._on_work_block)
        self.monitor.context.connect(self._on_context)
        self.monitor.reward.connect(self._award)
        self.monitor.obeyed.connect(self._on_obeyed)
        self.settings_page.avatar_changed.connect(
            lambda: self._show_message(self._last_emotion, self.companion_text.text()))
        self.companion.message.connect(self._show_message)
        self._create_tray()
        self._update_xp_ui()
        QTimer.singleShot(500, self.companion.greet)
        self.projects_page.refresh()

    def _make_icon(self):
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#533483"))
        p.drawRoundedRect(2, 2, 60, 60, 14, 14)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI Emoji", 28))
        p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "😏")
        p.end()
        return QIcon(pix)

    def _create_tray(self):
        self.tray = QSystemTrayIcon(self._make_icon(), self)
        menu = QMenu()
        act_show = menu.addAction("📂 Открыть окно")
        act_show.triggered.connect(self._show_window)
        self.act_monitor = menu.addAction("👁 Мониторинг активности")
        self.act_monitor.setCheckable(True)
        self.act_monitor.setChecked(self.monitor.enabled)
        self.act_monitor.toggled.connect(self._tray_monitor_toggled)
        act_settings = menu.addAction("⚙ Настройки")
        act_settings.triggered.connect(self._open_settings)
        menu.addSeparator()
        act_quit = menu.addAction("❌ Выход")
        act_quit.triggered.connect(self._quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_monitor_toggled(self, on):
        self.monitor.set_enabled(on)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _minimize_to_tray(self):
        self.hide()
        push_notify("Кай", self.bank.say("minimize"))

    def _open_settings(self):
        self._show_window()
        self.stack.setCurrentIndex(5)

    def _quit(self):
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        self.tray.hide()
        QApplication.quit()

    def _on_obeyed(self):
        if self.gamification.add_obey():
            self._unlock("obedient")

    def _on_context(self, cat, title):
        t = title[:60]
        if cat == "off":
            self.status_bar_widget.context_label.setText("👁 мониторинг выключен")
        elif cat == "distract":
            site = self.monitor._detect_distract(title.lower()) or "сайт"
            self.status_bar_widget.context_label.setText(f"👁 {site}: {t}")
        elif cat == "work":
            app = self.monitor._detect_app(title.lower()) or "работа"
            self.status_bar_widget.context_label.setText(f"👁 {app}: {t}")
        elif cat == "browse":
            self.status_bar_widget.context_label.setText(f"👁 браузер: {t}")
        elif cat == "self":
            self.status_bar_widget.context_label.setText("👁 Кай")
        else:
            self.status_bar_widget.context_label.setText(f"👁 {t or '—'}")

    def _on_monitor_alert(self, emotion, text):
        if self.monitor.voice_enabled:
            self.companion.say_aloud(emotion, text)
        else:
            self.companion.say(emotion, text)
        self._toast("Кай", text)
        if self.monitor.push_enabled:
            push_notify("Кай", text)

    def _on_work_block(self, minutes):
        self.companion.on_work_block(minutes)
        self._award(20)
        self._toast("Кай", f"Фокус-блок {minutes} минут! +20 XP")
        if self.monitor.push_enabled:
            push_notify("Кай", f"{minutes} минут непрерывной работы! +20 XP")

    def _on_tab(self, name):
        if name == "tasks":
            self.stack.setCurrentIndex(0)
        elif name == "game":
            self.stack.setCurrentIndex(4)
        else:
            self.stack.setCurrentIndex(5)
        self.nav.set_active(name)

    def _on_stack_changed(self, idx):
        if idx == 4:
            self.game_page.refresh()
            self.nav.set_active("game")
        elif idx == 5:
            self.settings_page.sync()
            self.nav.set_active("settings")
        else:
            self.nav.set_active("tasks")

    def _show_message(self, emotion, text):
        self._last_emotion = emotion
        pix = self.avatar.pixmap_for(emotion, 46)
        if pix:
            self.status_bar_widget.companion_avatar.setPixmap(pix)
        else:
            self.status_bar_widget.companion_avatar.clear()
            emojis = {"happy": "😊", "neutral": "😏", "worried": "🥺",
                      "sarcastic": "😈", "excited": "🤩", "caring": "💜"}
            self.status_bar_widget.companion_avatar.setText(emojis.get(emotion, "😏"))
        self.status_bar_widget.companion_text.setText(text)

    def _update_xp_ui(self):
        g = self.gamification
        self.status_bar_widget.level_label.setText(f"⚔️ Ур. {g.data['level']}")
        self.status_bar_widget.xp_bar.setValue(g.progress_percent())
        self.status_bar_widget.xp_label.setText(f"✨ {g.data['xp']}/{g.next_level_xp()}")

    def _toast(self, title, text):
        toast = Toast(title, text)
        toast.closed.connect(self._remove_toast)
        screen = QApplication.primaryScreen().availableGeometry()
        y = 60 + 90 * len(self.toasts)
        toast.move(screen.right() - 340, y)
        self.toasts.append(toast)
        toast.show()

    def _remove_toast(self, toast):
        if toast in self.toasts:
            self.toasts.remove(toast)

    def _unlock(self, key):
        if self.gamification.unlock(key):
            name, desc = ACHIEVEMENTS[key]
            self._toast("Кай", f"🏆 Достижение: {name}")
            self.companion.say_aloud("excited", self.bank.say("achievement", name=name))

    def _award(self, amount):
        amount = int(amount * self.gamification.xp_multiplier())
        gained, leveled, level = self.gamification.add_xp(amount)
        self._update_xp_ui()
        if leveled:
            self.companion.on_level_up(level)
            if level >= 5:
                self._unlock("level_5")
        return gained

    def _hit_enemy(self, amount, source):
        emoji, name, max_hp, desc = self.battle.current()
        defeated = self.battle.damage(amount)
        if defeated:
            self.companion.on_enemy_defeated(name)
            self._award(150)
            self._unlock("dragon_slayer")
            if self.battle.kills() >= 5:
                self._unlock("hunter5")
        else:
            self.companion.on_enemy_hit(name, amount, self.battle.hp())
        self.game_page.refresh()

    def _quest_progress(self, key):
        reward = self.quests.progress(key)
        if reward:
            self._award(reward)
            self.companion.on_quest_done(reward)
        self.game_page.refresh()

    def _on_project_created(self, name):
        self._award(20)
        self.companion.on_project_created(name)
        self._unlock("first_project")
        self._hit_enemy(30, "проект")
        self._quest_progress("create1")

    def _on_task_created(self, name):
        self._award(15)
        self.companion.on_task_created(name)
        self._unlock("first_task")
        self._hit_enemy(30, "задача")
        self._quest_progress("create1")

    def _on_rehearsal_done(self):
        self._award(25)
        self.gamification.data["rehearsals"] = self.gamification.data.get("rehearsals", 0) + 1
        self.gamification._save()
        self.companion.on_rehearsal_done()
        self._unlock("first_rehearsal")
        self._hit_enemy(50, "репетиция")
        self._quest_progress("reh1")

    def _on_task_done_toggled(self, now_done, name):
        if now_done:
            self._award(100)
            self.gamification.data["tasks_done"] = self.gamification.data.get("tasks_done", 0) + 1
            self.gamification._save()
            self.companion.on_task_done(name)
            self._unlock("first_done")
            if self.gamification.data["tasks_done"] >= 10:
                self._unlock("ten_tasks")
            if self.gamification.update_streak():
                self._unlock("streak_3")
            pid = self.task_page.current_project_id
            p = self.data.get_project(pid)
            if p and p["tasks"] and all(t["done"] for t in p["tasks"]):
                self._unlock("all_done")
            self._hit_enemy(100, "задача")
            self._quest_progress("tasks2")
        else:
            self.companion.on_task_undone()

    def _open_project(self, project_id):
        self.project_page.load_project(project_id)
        self.stack.setCurrentIndex(1)

    def _back_to_projects(self):
        self.projects_page.refresh()
        self.stack.setCurrentIndex(0)

    def _open_task(self, project_id, task_id):
        self.task_page.load_task(project_id, task_id)
        self.stack.setCurrentIndex(2)

    def _back_to_project(self):
        self.project_page.refresh()
        self.stack.setCurrentIndex(1)

    def _start_rehearsal(self, steps, task_name, mode):
        self.companion.on_rehearsal_start(task_name, mode)
        self.rehearsal_page.start(steps, task_name, mode)
        self.stack.setCurrentIndex(3)

    def _back_to_task(self):
        self.stack.setCurrentIndex(2)
