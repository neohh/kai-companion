"""
core.companion — Компаньон Кай: фразы + озвучка (фасад над bank и voice).
Владельцы: Companion (сигнал message).
Зависимости: time; PyQt6 (QObject, pyqtSignal).
"""
import time

from PyQt6.QtCore import pyqtSignal, QObject


# ============================================
# КОМПАНЬОН КАЙ
# ============================================
class Companion(QObject):
    message = pyqtSignal(str, str)

    def __init__(self, voice_engine, bank):
        super().__init__()
        self.voice = voice_engine
        self.bank = bank
        self.rate_pct = 30
        self.pause_per_char = 0.02

    def set_speed_value(self, value):
        self.rate_pct = 50 - 2 * value
        self.pause_per_char = value * 0.002

    def say(self, emotion, text):
        self.message.emit(emotion, text)

    def say_aloud(self, emotion, text):
        self.message.emit(emotion, text)
        self.voice.speak(text, block=False, rate_pct=0, emotion=emotion)

    def speak_with_pause(self, text, emotion="caring"):
        self.voice.speak(text, block=True, rate_pct=self.rate_pct, emotion=emotion)
        time.sleep(max(1.0, len(text) * self.pause_per_char))

    def greet(self):
        self.say_aloud("neutral", self.bank.say("greet"))

    def on_project_created(self, name):
        self.say_aloud("excited", self.bank.say("project_created", name=name))

    def on_task_created(self, name):
        self.say("happy", self.bank.say("task_created", name=name))

    def on_rehearsal_start(self, name, mode):
        key = "rehearsal_intro_voice" if mode == "voice" else "rehearsal_intro_manual"
        if mode == "voice":
            self.say_aloud("excited", self.bank.say(key, name=name))
        else:
            self.say("excited", self.bank.say(key, name=name))

    def reh_line1(self):
        return self.bank.say("reh_line1")

    def reh_line2(self):
        return self.bank.say("reh_line2")

    def reh_step(self, i, step):
        return self.bank.say("reh_step", i=i, step=step)

    def reh_end(self):
        return self.bank.say("reh_end")

    def on_rehearsal_done(self):
        self.say_aloud("happy", self.bank.say("rehearsal_done"))

    def on_task_done(self, name):
        self.say_aloud("happy", self.bank.say("task_done", name=name))

    def on_task_undone(self):
        self.say("neutral", self.bank.say("task_undone"))

    def on_level_up(self, level):
        self.say_aloud("excited", self.bank.say("level_up", level=level))

    def on_deleted(self):
        self.say("neutral", self.bank.say("deleted"))

    def on_renamed(self):
        self.say("neutral", self.bank.say("renamed"))

    def on_steps_updated(self):
        self.say("happy", self.bank.say("steps_updated"))

    def on_empty_steps(self):
        self.say("worried", self.bank.say("empty_steps"))

    def on_enemy_hit(self, name, amount, hp_left):
        self.say("sarcastic", self.bank.say("enemy_hit", name=name, amount=amount, hp_left=hp_left))

    def on_enemy_defeated(self, name):
        self.say_aloud("excited", self.bank.say("enemy_defeated", name=name))

    def on_quest_done(self, reward):
        self.say("happy", self.bank.say("quest_done", reward=reward))

    def on_work_block(self, minutes):
        self.say_aloud("excited", self.bank.say("work_block", minutes=minutes))
