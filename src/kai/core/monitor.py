"""
core.monitor — мониторинг активных окон: «дрессировка» и контекст.
Владельцы: ActivityMonitor (сигналы alert, work_block, context, reward, obeyed).
Зависимости: json, time, random, pathlib; PyQt6 (QObject, QTimer, pyqtSignal);
kai.constants (DEFAULT_DISTRACT, DEFAULT_WORK, DISTRACT_NAMES, BROWSER_KEYS, APP_NAMES);
kai.sys_utils.get_foreground_title.
"""
import json
import time
import random
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

from kai.constants import (DEFAULT_DISTRACT, DEFAULT_WORK, DISTRACT_NAMES,
                           BROWSER_KEYS, APP_NAMES)
from kai.sys_utils import get_foreground_title


# ============================================
# МОНИТОР: ДРЕССИРОВКА + КОНТЕКСТ
# ============================================
class ActivityMonitor(QObject):
    alert = pyqtSignal(str, str)
    work_block = pyqtSignal(int)
    context = pyqtSignal(str, str)
    reward = pyqtSignal(int)
    obeyed = pyqtSignal()

    def __init__(self, data_dir, bank):
        super().__init__()
        self.bank = bank
        self.cfg_file = Path(data_dir) / "monitor.json"
        cfg = self._load_cfg()
        self.enabled = cfg.get("enabled", True)
        self.push_enabled = cfg.get("push_enabled", True)
        self.voice_enabled = cfg.get("voice_enabled", True)
        self.grace = cfg.get("grace", 60)
        self.remind_every = cfg.get("remind_every", 300)
        self.compliance = cfg.get("compliance", 120)
        self.cheer_every = cfg.get("cheer_every", 240)
        self.distract = cfg.get("distract", DEFAULT_DISTRACT)
        self.work = cfg.get("work", DEFAULT_WORK)
        self.state = "neutral"
        self.state_start = time.time()
        self.next_remind = 0
        self.remind_count = 0
        self.work_seconds = 0
        self.last_react = 0
        self.distract_start = None
        self.cur_site = ""
        self.next_cheer = 0
        self._last_ctx = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll)
        self.timer.start(5000)

    def _load_cfg(self):
        try:
            if self.cfg_file.exists():
                with open(self.cfg_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_cfg(self):
        try:
            with open(self.cfg_file, "w", encoding="utf-8") as f:
                json.dump({"enabled": self.enabled, "push_enabled": self.push_enabled,
                           "voice_enabled": self.voice_enabled, "grace": self.grace,
                           "remind_every": self.remind_every,
                           "compliance": self.compliance, "cheer_every": self.cheer_every,
                           "distract": self.distract, "work": self.work}, f)
        except Exception:
            pass

    def apply_settings(self, enabled, push, voice, grace, remind, compliance, cheer, distract, work):
        self.enabled = enabled
        self.push_enabled = push
        self.voice_enabled = voice
        self.grace = grace
        self.remind_every = remind
        self.compliance = compliance
        self.cheer_every = cheer
        self.distract = distract
        self.work = work
        self.save_cfg()
        if not enabled:
            self.context.emit("off", "")

    def set_enabled(self, on):
        self.enabled = on
        self.save_cfg()
        if not on:
            self.context.emit("off", "")

    def _detect_app(self, title):
        for key, name in APP_NAMES:
            if key in title:
                return name
        return None

    def _detect_distract(self, title):
        for key in self.distract:
            if key in title:
                return DISTRACT_NAMES.get(key, key.capitalize())
        return None

    def _poll(self):
        if not self.enabled:
            return
        title = get_foreground_title()
        low = title.lower()
        if not title or "kai" in low or "кай" in low:
            cat = "self"
        elif self._detect_distract(low):
            cat = "distract"
        elif any(k in low for k in self.work):
            cat = "work"
        elif any(k in low for k in BROWSER_KEYS):
            cat = "browse"
        else:
            cat = "neutral"
        if (cat, title) != self._last_ctx:
            self._last_ctx = (cat, title)
            self.context.emit(cat, title)
        now = time.time()
        if cat != self.state:
            prev = self.state
            self.state = cat
            self.state_start = now
            self.remind_count = 0
            self.next_remind = now + self.grace
            if cat == "distract":
                self.distract_start = now
                self.cur_site = self._detect_distract(low) or "Сайт"
                self.alert.emit("sarcastic", self.bank.say("distract_now", site=self.cur_site))
                self.last_react = now
                self.remind_count = 1
                return
            if prev == "distract":
                dur = now - (self.distract_start or now)
                if dur <= self.compliance:
                    self.alert.emit("happy", self.bank.say("good_boy"))
                    self.reward.emit(15)
                    self.obeyed.emit()
                    if random.random() < 0.3:
                        self.alert.emit("excited", self.bank.say("good_boy_bonus"))
                        self.reward.emit(25)
                else:
                    self.alert.emit("happy", self.bank.say("welcome_back"))
                    self.reward.emit(5)
                self.last_react = now
            if cat == "work":
                self.next_cheer = now + self.cheer_every
                if now - self.last_react >= 30:
                    app = self._detect_app(low) or "рабочая прога"
                    self.alert.emit("excited", self.bank.say("praise_work", app=app))
                    self.last_react = now
            elif cat == "browse" and now - self.last_react >= 30:
                self.alert.emit("sarcastic", self.bank.say("browse_tease"))
                self.last_react = now
            return
        dur = now - self.state_start
        if cat == "distract":
            if now >= self.next_remind:
                self.alert.emit("worried", self.bank.say("distract_repeat",
                                                          min=int(dur // 60), site=self.cur_site))
                self.remind_count += 1
                self.next_remind = now + self.remind_every
        elif cat == "work":
            self.work_seconds += 5
            if now >= self.next_cheer:
                self.alert.emit("excited", self.bank.say("work_keep"))
                self.next_cheer = now + self.cheer_every + random.randint(-30, 30)
            if self.work_seconds >= 25 * 60:
                self.work_seconds = 0
                self.work_block.emit(25)
