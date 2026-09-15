"""
ui.main_window — главное окно: composition root, создание всех сервисов и связывание сигналов.
Владельцы: MainWindow.
Зависимости: PyQt6; core.* (DataManager, Gamification, BattleManager, DailyQuests,
PhraseBank, AvatarManager, ActivityMonitor, Companion); voice.engine.VoiceEngine;
ui.theme.STYLESHEET; ui.nav.NavBar; ui.status_bar.StatusBar; ui.widgets.Toast;
ui.choice_toast.ChoiceToast; ui.pages.*; kai.constants.ACHIEVEMENTS;
kai.sys_utils.push_notify; kai.core.relationship.Mood; kai.core.contracts.DebtBook;
kai.core.rituals.EveningRitual; kai.voice.seasons.SeasonWheel.
Часть C: kai.core.economy.Wallet; kai.core.loot.ChestEngine; kai.core.wheel.WheelFortune;
kai.core.collections.MoodCollection; kai.core.wagers.WagerBook; ui.pages.loot_page.LootPage;
ui.loot_toast.LootToast.
"""
import sys
from datetime import datetime, date

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
from kai.core.relationship import Mood
from kai.core.contracts import DebtBook
from kai.core.rituals import EveningRitual
from kai.core.economy import Wallet
from kai.core.loot import ChestEngine
from kai.core.wheel import WheelFortune
from kai.core.collections import MoodCollection
from kai.core.wagers import WagerBook
from kai.voice.engine import VoiceEngine
from kai.voice.seasons import SeasonWheel
from kai.ui.theme import STYLESHEET
from kai.ui.nav import NavBar
from kai.ui.status_bar import StatusBar
from kai.ui.widgets import Toast
from kai.ui.choice_toast import ChoiceToast
from kai.ui.loot_toast import LootToast
from kai.ui.pages.loot_page import LootPage
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
        self.monitor = ActivityMonitor(self.data.data_dir, self.bank)
        # --- Часть B: живой Кай ---
        self.mood = Mood(self.gamification.save_file)
        self.debts = DebtBook(self.gamification.save_file)
        self.rituals = EveningRitual(self.gamification.save_file)
        self.seasons = SeasonWheel()
        self.companion = Companion(self.voice_engine, self.bank,
                                   mood=self.mood, debts=self.debts)
        self.mood.daily_decay()
        # --- Часть C: азарт-слой ---
        self.wallet = Wallet(self.gamification.save_file)
        self.chests = ChestEngine(self.gamification.save_file)
        self.wheel = WheelFortune(self.gamification.save_file)
        self.collection = MoodCollection(self.gamification.save_file)
        self.wagers = WagerBook(self.gamification.save_file, self.gamification)
        self.toasts = []
        self.choice_toasts = []
        self.loot_toasts = []
        self._pending_nudge = None
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
                                          self.avatar, self.companion, self.bank,
                                          mood=self.mood, rituals=self.rituals,
                                          seasons=self.seasons, chests=self.chests,
                                          wheel=self.wheel, wagers=self.wagers)
        self.stack.addWidget(self.projects_page)   # 0
        self.stack.addWidget(self.project_page)    # 1
        self.stack.addWidget(self.task_page)       # 2
        self.stack.addWidget(self.rehearsal_page)  # 3
        self.stack.addWidget(self.game_page)       # 4
        self.stack.addWidget(self.settings_page)   # 5
        # --- Часть C: страница сокровищницы ---
        self.loot_page = LootPage(self.wallet, self.chests, self.wheel, self.collection)
        self.stack.addWidget(self.loot_page)       # 6
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
        # --- Часть B: связывание выборов и ритуала ---
        self.monitor.choice_offered.connect(self._on_choice_offered)
        self.monitor.debt_taken.connect(self._on_debt_taken)
        self.settings_page.avatar_changed.connect(
            lambda: self._show_message(self._last_emotion, self.companion_text.text()))
        self.companion.message.connect(self._show_message)
        self._create_tray()
        self._update_xp_ui()
        self._update_mood_ui()
        QTimer.singleShot(500, self.companion.greet)
        QTimer.singleShot(3500, self._nudge_rehearsal)
        self.projects_page.refresh()
        # таймер ритуала/сезонов: проверка раз в минуту
        self._ritual_timer = QTimer(self)
        self._ritual_timer.timeout.connect(self._check_ritual)
        self._ritual_timer.start(60 * 1000)
        self._check_season()
        # Часть B: лимит похвалы для периодических подбадриваний монитора
        self.monitor.praise_gate = self.mood.praise_allowed
        self.monitor.praise_mark = self.mood.mark_praise
        # --- Часть C: связывание экономики и лута ---
        self.wallet.economy_changed.connect(self._update_wallet_ui)
        self.wheel.spun.connect(self._on_wheel_result)
        self.wagers.wager_won.connect(self._on_wager_won)
        self.wagers.wager_lost.connect(self._on_wager_lost)
        self.collection.set_completed.connect(
            lambda: self.companion.say_aloud("excited", self.bank.say("set_complete")))
        self._update_wallet_ui()
        self._schedule_double_drop_hour()

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
        # Часть B: послушание греет Кая
        self.mood.on_obeyed()
        self._update_mood_ui()
        # Часть C: монеты за послушание
        if self._ludo_on():
            self._hook_reward("obedience")

    # --- Побуждение к репетиции при входе ---
    def _pick_rehearsal_candidate(self):
        """Незавершённая задача с шагами (свежая первой)."""
        best = None
        for p in self.data.get_projects():
            for t in p["tasks"]:
                if t["done"] or not t["steps"]:
                    continue
                if best is None or t.get("created_at", "") > best[0]:
                    best = (t.get("created_at", ""), p["id"], t)
        if best is None:
            return None
        _, pid, t = best
        return pid, t

    def _nudge_rehearsal(self):
        """При входе: предложить пройти репетицию первой незавершённой задачи."""
        import datetime
        today = datetime.date.today().isoformat()
        if self.gamification.data.get("nudge_date") == today:
            return  # раз в день
        if self.mood.boycotting():
            return  # бойкот: Кай молчит
        cand = self._pick_rehearsal_candidate()
        if not cand:
            return
        pid, task = cand
        self.gamification.data["nudge_date"] = today
        self.gamification._save()
        self._pending_nudge = (pid, task["id"])
        text = self.bank.say("rehearsal_nudge", name=task["name"])
        self.companion.say_aloud("caring", text)
        self.monitor.offer_choice("rehearsal_nudge", text,
                                  [("start", "🎭 Пройти сейчас"),
                                   ("later", "🕒 Позже"),
                                   ("ignore", "🙈 Игнорирую")])

    def _resolve_nudge_choice(self, option):
        cand = getattr(self, "_pending_nudge", None)
        self._pending_nudge = None
        if option == "start" and cand:
            pid, tid = cand
            task = self.data.get_task(pid, tid)
            if task:
                self._start_rehearsal(task["steps"], task["name"], "voice")
        elif option == "later":
            self.companion.say("neutral", self.bank.say("nudge_later"))
        elif option == "ignore":
            res = self.mood.on_ignored()
            self.rituals.count_ignored()
            self._update_mood_ui()
            if res["strikes"] == 1:
                self.companion.say("worried", self.bank.say("cold_pack"))
            elif res["boycott_started"]:
                self.companion.say("cold", self.bank.say("boycott_start"))

    # --- Часть B: выборы, долги, ритуал, сезоны ---
    def _on_choice_offered(self, choice_id, text, choices):
        toast = ChoiceToast("Кай", text, choices, choice_id=choice_id)
        toast.answered.connect(self._on_choice_answered)
        screen = QApplication.primaryScreen().availableGeometry()
        y = 60 + 90 * (len(self.toasts) + len(self.choice_toasts))
        toast.move(screen.right() - 340, y)
        self.choice_toasts.append(toast)
        toast.show()

    def _on_choice_answered(self, toast, option):
        if toast in self.choice_toasts:
            self.choice_toasts.remove(toast)
        if getattr(toast, "choice_id", "") == "rehearsal_nudge":
            self._resolve_nudge_choice(option)
            return
        if option == "ignore":
            res = self.mood.on_ignored()
            self.rituals.count_ignored()
            if res["strikes"] == 1:
                self.companion.say("worried", self.bank.say("cold_pack"))
            elif res["strikes"] == 2:
                self.companion.say("sarcastic", self.bank.say("praise_scarcity"))
            elif res["boycott_started"]:
                self.companion.say("cold", self.bank.say("boycott_start"))
        else:
            self.rituals.count_answered()
            self.mood.on_answered()
        self.monitor.resolve_choice(getattr(toast, "choice_id", "") or "distract_exit", option)
        self._update_mood_ui()

    def _on_debt_taken(self, minutes):
        self.debts.take_debt(minutes)
        self._toast("Кай", f"Долг +{minutes} мин. Всего: {self.debts.phrase()}")

    def _update_mood_ui(self):
        em = self.mood.status_emoji().get(self.mood.status(), "😏")
        if self.mood.status() == "boycott":
            self.status_bar_widget.mood_label.setText(f"silent {self.mood.minutes_to_end()}м")
        else:
            self.status_bar_widget.mood_label.setText(f"{em} {self.mood.closeness()}")

    def _check_ritual(self):
        if self.rituals.pending():
            return  # ждём ответа, не спамим
        if self.rituals.due_now():
            self.rituals.start()
            self.companion.say_aloud("caring", self.bank.say("evening_ritual"))
        elif self.rituals.negotiation_due(0.5):
            self.rituals.mark_negotiated()
            self.companion.say_aloud("worried", self.bank.say("negotiation"))

    def _check_season(self):
        if self.seasons.changes_today():
            s = self.seasons.current()
            self.companion.say("neutral", self.bank.say("season_announce",
                                                        season=s["name"], emoji=s["emoji"]))

    # --- Часть C: азарт-слой ---
    def _ludo_on(self):
        """Этический ограничитель №1: слой целиком отключаем галочкой."""
        return (self.chests.enabled() and self.wheel.enabled()
                and self.wagers.enabled())

    def _coin_mult(self):
        """Множитель монет: двойной дроп-час x2."""
        return 2.0 if self._is_double_drop_hour() else 1.0

    def _is_double_drop_hour(self):
        return self.rituals.data.get("double_drop_hour") == datetime.now().hour

    def _schedule_double_drop_hour(self):
        """Один случайный час в день — двойной дроп-час, анонс голосом."""
        import random as _r
        rng = _r.Random(date.today().isoformat())
        if self.rituals.data.get("double_drop_date") != date.today().isoformat():
            self.rituals.data["double_drop_date"] = date.today().isoformat()
            self.rituals.data["double_drop_hour"] = rng.randint(10, 22)
            self.rituals.save()
        self._ddh_announced = False
        self._ddh_timer = QTimer(self)
        self._ddh_timer.timeout.connect(self._check_double_drop_hour)
        self._ddh_timer.start(60 * 1000)

    def _check_double_drop_hour(self):
        if self._is_double_drop_hour() and not getattr(self, "_ddh_announced", False):
            self._ddh_announced = True
            self.companion.say_aloud("excited", self.bank.say("double_drop_hour"))
            self._toast("Кай", "⏰ Час двойного дропа! Монеты и шанс дропа x2")

    def _hook_reward(self, source):
        """Хук экономики: вызывать при task_done/rehearsal/focus/quest/obedience."""
        self.wallet.earn(source, self._coin_mult())
        if source == "focus_block":
            self.wheel.add_charge("focus_block")
        elif source == "daily_quest":
            self.wheel.add_charge("daily_quest")

    def _on_wheel_result(self, res):
        loot = res["loot"]
        t = loot.get("type")
        if t == "coins":
            self.wallet.data["wallet"]["coins"] += loot["amount"]
            self.wallet.save()
            self.companion.say("excited", self.bank.say("wheel_win", prize=res["label"]))
        elif t == "token":
            self.wallet.add_token(loot["token"])
            self.companion.say("excited", self.bank.say("wheel_win", prize=res["label"]))
        elif t == "grace":
            self.debts.pardon(15)
            self.companion.say("happy", self.bank.say("wheel_win", prize=res["label"]))
        elif t == "chest":
            opened = self.chests.open_chest(drop_chance=1.0)
            if opened:
                self._show_loot(opened[0], opened[1])
        elif t == "empty":
            if res["almost_jackpot"]:
                self.companion.say("sarcastic", self.bank.say("wheel_nearmiss"))
                self._show_loot(None, None, near_miss=True)
            else:
                self.companion.say("neutral", self.bank.say("wheel_empty"))
        if self.stack.currentIndex() == 6:
            self.loot_page.refresh()

    def _show_loot(self, rarity, loot, near_miss=False):
        toast = LootToast(rarity, loot, near_miss_label="🎯 Стрелка у самого джекпота! Почти!~" if near_miss else None)
        screen = QApplication.primaryScreen().availableGeometry()
        y = 60 + 90 * len(self.toasts)
        toast.move(screen.right() - 360, y)
        self.loot_toasts.append(toast)
        toast.show()

    def _apply_loot(self, loot):
        """Начислить содержимое сундука."""
        t = loot.get("type")
        if t == "coins":
            self.wallet.data["wallet"]["coins"] += loot["amount"]
            self.wallet.save()
        elif t == "token":
            self.wallet.add_token(loot["token"])
        elif t == "grace":
            self.debts.pardon(999)
        elif t == "card":
            self.collection.add_card(loot["card_id"])
        # xp_mult/cosmetic хранятся в инвентаре как ожидающие применения

    def _update_wallet_ui(self):
        self.status_bar_widget.mood_label.setToolTip(
            f"Монеты: {self.wallet.coins()}")
        if self.stack.currentIndex() == 6:
            self.loot_page.refresh()

    def _on_wager_won(self, wid, payout):
        self.companion.say_aloud("excited", self.bank.say("wager_win"))
        self._update_xp_ui()

    def _on_wager_lost(self, wid, amount):
        self.companion.say("sarcastic", self.bank.say("wager_lose"))
        self._update_xp_ui()

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
        # Часть C: монеты за фокус + заряд колеса + гашение долга
        if self._ludo_on():
            self._hook_reward("focus_block")
            self.debts.repay(25)

    def _on_tab(self, name):
        if name == "tasks":
            self.stack.setCurrentIndex(0)
        elif name == "game":
            self.stack.setCurrentIndex(4)
        elif name == "loot":
            self.stack.setCurrentIndex(6)
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
        elif idx == 6:
            self.loot_page.refresh()
            self.nav.set_active("loot")
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
        # Часть C: перманентный бонус коллекции
        amount = int(amount * self.gamification.xp_multiplier() * self.collection.bonus_multiplier())
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
        if self._ludo_on():
            self._hook_reward("create1")

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
        # Часть C: монеты + шанс сундука + карта коллекции
        if self._ludo_on():
            self._hook_reward("rehearsal_done")
            opened = self.chests.open_chest(drop_chance=0.3)
            if opened:
                self._apply_loot(opened[1])
                self._show_loot(*opened)
                self.companion.say("excited", self.bank.say(f"drop_{opened[0]}"))

    def _on_task_done_toggled(self, now_done, name):
        if now_done:
            # Часть C: крит-ролл и стрик-множитель (только при включённом слое)
            if self._ludo_on():
                mult, kind = self.gamification.roll_crit()
                mult *= self.gamification.streak_multiplier()
                if kind == "supercrit":
                    self.companion.say_aloud("excited", self.bank.say("supercrit"))
                elif kind == "crit":
                    self.companion.say_aloud("excited", self.bank.say("crit"))
            else:
                mult = 1.0
            self._award(int(100 * mult))
            # Часть C: расчёт активных ставок по этой задаче
            for w in self.wagers.active():
                if w["task"] == name:
                    self.wagers.settle(w["id"], True)
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
            # Часть C: монеты + шанс сундука
            if self._ludo_on():
                self._hook_reward("task_done")
                opened = self.chests.open_chest(drop_chance=0.5)
                if opened:
                    self._apply_loot(opened[1])
                    self._show_loot(*opened)
                    self.companion.say("excited", self.bank.say(f"drop_{opened[0]}"))
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
