"""
ui.pages.settings — вкладка настроек: мониторинг, голос/движок, манеры, фразы, спрайты.
Владельцы: SettingsPage.
Зависимости: PyQt6; kai.voice.styles (GEMINI_VOICES, STYLE_PROMPTS);
kai.constants.EMOTIONS_RU; kai.core.phrases (DEFAULT_PHRASES, EVENT_LABELS);
kai.sys_utils.push_notify не используется здесь; синк через sync() при открытии вкладки.
"""
import threading

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFrame, QLineEdit, QComboBox, QCheckBox, QSlider,
                             QSpinBox, QPlainTextEdit, QScrollArea, QFileDialog)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import pyqtSignal

from kai.voice.styles import GEMINI_VOICES, STYLE_PROMPTS
from kai.constants import EMOTIONS_RU
from kai.core.phrases import DEFAULT_PHRASES, EVENT_LABELS


# ============================================
# ВКЛАДКА НАСТРОЕК
# ============================================
class SettingsPage(QWidget):
    avatar_changed = pyqtSignal()
    _gemini_test_done = pyqtSignal(object)

    def __init__(self, monitor, voice, avatar, companion, bank, mood=None, rituals=None, seasons=None,
                 chests=None, wheel=None, wagers=None):
        super().__init__()
        self.monitor = monitor
        self.voice = voice
        self.avatar = avatar
        self.companion = companion
        self.bank = bank
        self.mood = mood
        self.rituals = rituals
        self.seasons = seasons
        self.chests = chests
        self.wheel = wheel
        self.wagers = wagers
        self.previews = {}
        self._gemini_test_btn = None
        self._gemini_test_done.connect(self._on_gemini_test_done)
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 20, 30, 20)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        title = QLabel("⚙ Настройки Кая")
        title.setStyleSheet("font-size: 26px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        # --- МОНИТОРИНГ ---
        mon_frame = QFrame()
        mf = QVBoxLayout(mon_frame)
        mt = QLabel("👁 Мониторинг и дрессировка")
        mt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        mf.addWidget(mt)
        self.chk_monitor = QCheckBox("Следить за активными окнами")
        mf.addWidget(self.chk_monitor)
        self.chk_push = QCheckBox("Пуш-уведомления Windows")
        mf.addWidget(self.chk_push)
        self.chk_voice = QCheckBox("Озвучивать уведомления голосом")
        mf.addWidget(self.chk_voice)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Считать послушанием, если вышел за (сек):"))
        self.spin_compliance = QSpinBox(); self.spin_compliance.setRange(10, 600)
        row1.addWidget(self.spin_compliance); row1.addStretch()
        mf.addLayout(row1)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Повторные напоминания каждые (сек):"))
        self.spin_grace = QSpinBox(); self.spin_grace.setRange(10, 600)
        row2.addWidget(self.spin_grace); row2.addStretch()
        mf.addLayout(row2)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Подбадривать во время работы каждые (сек):"))
        self.spin_cheer = QSpinBox(); self.spin_cheer.setRange(60, 1800)
        row3.addWidget(self.spin_cheer); row3.addStretch()
        mf.addLayout(row3)
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Реакции на смены окон не чаще (сек):"))
        self.spin_remind = QSpinBox(); self.spin_remind.setRange(10, 600)
        row4.addWidget(self.spin_remind); row4.addStretch()
        mf.addLayout(row4)
        mf.addWidget(QLabel("Отвлекающие слова (через запятую):"))
        self.edit_distract = QLineEdit()
        mf.addWidget(self.edit_distract)
        mf.addWidget(QLabel("Рабочие программы (через запятую):"))
        self.edit_work = QLineEdit()
        mf.addWidget(self.edit_work)
        btn_save_mon = QPushButton("💾 Сохранить мониторинг")
        btn_save_mon.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_mon.clicked.connect(self._save_monitor)
        mf.addWidget(btn_save_mon)
        layout.addWidget(mon_frame)
        # --- ГОЛОС / ДВИЖОК ---
        voice_frame = QFrame()
        vf = QVBoxLayout(voice_frame)
        vt = QLabel("🎙 Голос и движок озвучки")
        vt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        vf.addWidget(vt)
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["edge-tts (быстрый, без ключа)", "Gemini TTS (живые интонации по описанию)"])
        vf.addWidget(self.engine_combo)
        vf.addWidget(QLabel("API-ключ Gemini (AIza...):"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Вставь ключ из aistudio.google.com → Get API key")
        vf.addWidget(self.key_edit)
        vf.addWidget(QLabel("Прокси для Gemini (если регион с геоблоком, напр. http://127.0.0.1:8080):"))
        self.proxy_edit = QLineEdit()
        self.proxy_edit.setPlaceholderText("http://user:pass@host:port · socks5://host:port · пусто = без прокси")
        vf.addWidget(self.proxy_edit)
        vf.addWidget(QLabel("Тембр Gemini:"))
        self.gvoice_combo = QComboBox()
        self.gvoice_combo.addItems(GEMINI_VOICES)
        vf.addWidget(self.gvoice_combo)
        self.chk_emotion = QCheckBox("🎭 Доп. окраска edge-голоса (ffmpeg), когда Gemini недоступен")
        self.chk_emotion.toggled.connect(self.voice.set_emotion_fx)
        vf.addWidget(self.chk_emotion)
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["👩 Светлана", "👨 Дмитрий", "🤖 Системный (офлайн)"])
        vf.addWidget(self.voice_combo)
        preset_layout = QHBoxLayout()
        for label, vid, pitch, rate in [
            ("🎙 Стандарт", 0, 0, 0), ("🎀 Фембой", 1, 50, 10), ("🥺 Милый", 0, 35, 5)]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, v=vid, p=pitch, r=rate: self._apply_preset(v, p, r))
            preset_layout.addWidget(b)
        vf.addLayout(preset_layout)
        vf.addWidget(QLabel("Высота edge-голоса (pitch):"))
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-50, 80)
        vf.addWidget(self.pitch_slider)
        self.pitch_label = QLabel("")
        self.pitch_label.setStyleSheet("color: #888; background: transparent;")
        self.pitch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vf.addWidget(self.pitch_label)
        self.pitch_slider.valueChanged.connect(self._update_voice_labels)
        vf.addWidget(QLabel("Доп. темп edge-речи (%):"))
        self.rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.rate_slider.setRange(-30, 30)
        vf.addWidget(self.rate_slider)
        self.rate_label = QLabel("")
        self.rate_label.setStyleSheet("color: #888; background: transparent;")
        self.rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vf.addWidget(self.rate_label)
        self.rate_slider.valueChanged.connect(self._update_voice_labels)
        vbtn_layout = QHBoxLayout()
        btn_test = QPushButton("🔊 Тест")
        btn_test.clicked.connect(self._test_voice)
        vbtn_layout.addWidget(btn_test)
        btn_test_gemini = QPushButton("✨ Тест Gemini")
        btn_test_gemini.setToolTip("Озвучить через Gemini TTS сейчас (не сохраняя настройки). Показывает ошибку, если Gemini недоступен.")
        btn_test_gemini.clicked.connect(self._test_gemini)
        vbtn_layout.addWidget(btn_test_gemini)
        btn_save_voice = QPushButton("💾 Применить голос")
        btn_save_voice.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_voice.clicked.connect(self._save_voice)
        vbtn_layout.addWidget(btn_save_voice)
        vf.addLayout(vbtn_layout)
        self.voice_error_label = QLabel("")
        self.voice_error_label.setStyleSheet("color: #e74c3c; font-size: 11px; background: transparent;")
        self.voice_error_label.setWordWrap(True)
        self.voice_error_label.hide()
        vf.addWidget(self.voice_error_label)
        layout.addWidget(voice_frame)
        # --- УСЛОВИЯ РЕЧИ (стили Gemini) ---
        style_frame = QFrame()
        sf2 = QVBoxLayout(style_frame)
        stt = QLabel(" Условия речи (как говорить, по эмоциям)")
        stt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        sf2.addWidget(stt)
        shint = QLabel("Описание манеры для Gemini TTS. Редактируй под себя.")
        shint.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        sf2.addWidget(shint)
        self.style_combo = QComboBox()
        for key, label in EMOTIONS_RU.items():
            self.style_combo.addItem(label, key)
        self.style_combo.currentIndexChanged.connect(self._load_style_event)
        sf2.addWidget(self.style_combo)
        self.style_edit = QPlainTextEdit()
        self.style_edit.setFixedHeight(90)
        sf2.addWidget(self.style_edit)
        sbtn = QHBoxLayout()
        btn_save_style = QPushButton("💾 Сохранить манеру")
        btn_save_style.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_style.clicked.connect(self._save_style)
        sbtn.addWidget(btn_save_style)
        btn_reset_style = QPushButton("↩ Сбросить")
        btn_reset_style.clicked.connect(self._reset_style)
        sbtn.addWidget(btn_reset_style)
        sf2.addLayout(sbtn)
        layout.addWidget(style_frame)
        # --- ФРАЗЫ ---
        phr_frame = QFrame()
        pf = QVBoxLayout(phr_frame)
        pt = QLabel("💬 Фразы Кая")
        pt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        pf.addWidget(pt)
        phint = QLabel("Каждая строка — вариант фразы, выбирается случайно.\nПлейсхолдеры: {app}, {site}, {min}, {name}, {level}, {i}, {step}, {minutes}, {amount}, {hp_left}, {reward}")
        phint.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        pf.addWidget(phint)
        self.phr_combo = QComboBox()
        for key, label in EVENT_LABELS:
            self.phr_combo.addItem(label, key)
        self.phr_combo.currentIndexChanged.connect(self._load_phrase_event)
        pf.addWidget(self.phr_combo)
        self.phr_edit = QPlainTextEdit()
        self.phr_edit.setFixedHeight(140)
        pf.addWidget(self.phr_edit)
        pbtn = QHBoxLayout()
        btn_save_phr = QPushButton("💾 Сохранить фразы")
        btn_save_phr.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_phr.clicked.connect(self._save_phrases)
        pbtn.addWidget(btn_save_phr)
        btn_reset_phr = QPushButton("↩ Сбросить на стандарт")
        btn_reset_phr.clicked.connect(self._reset_phrases)
        pbtn.addWidget(btn_reset_phr)
        pf.addLayout(pbtn)
        layout.addWidget(phr_frame)
        # --- ОТНОШЕНИЯ (Часть B) ---
        rel_frame = QFrame()
        rf = QVBoxLayout(rel_frame)
        rt = QLabel("💜 Отношения")
        rt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        rf.addWidget(rt)
        rrow1 = QHBoxLayout()
        rrow1.addWidget(QLabel("Игноров до тихого бойкота:"))
        self.spin_ignore_threshold = QSpinBox()
        self.spin_ignore_threshold.setRange(1, 10)
        rrow1.addWidget(self.spin_ignore_threshold)
        rrow1.addStretch()
        rf.addLayout(rrow1)
        rrow2 = QHBoxLayout()
        rrow2.addWidget(QLabel("Лимит похвалы (раз в N минут):"))
        self.spin_praise_cooldown = QSpinBox()
        self.spin_praise_cooldown.setRange(5, 240)
        rrow2.addWidget(self.spin_praise_cooldown)
        rrow2.addStretch()
        rf.addLayout(rrow2)
        rrow3 = QHBoxLayout()
        rrow3.addWidget(QLabel("Время вечернего ритуала:"))
        self.spin_ritual_hour = QSpinBox()
        self.spin_ritual_hour.setRange(0, 23)
        self.spin_ritual_min = QSpinBox()
        self.spin_ritual_min.setRange(0, 59)
        self.spin_ritual_min.setSingleStep(5)
        rrow3.addWidget(self.spin_ritual_hour)
        rrow3.addWidget(QLabel(":"))
        rrow3.addWidget(self.spin_ritual_min)
        rrow3.addStretch()
        rf.addLayout(rrow3)
        self.lbl_season = QLabel("")
        self.lbl_season.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        rf.addWidget(self.lbl_season)
        btn_save_rel = QPushButton("💾 Сохранить отношения")
        btn_save_rel.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_rel.clicked.connect(self._save_relationship)
        rf.addWidget(btn_save_rel)
        layout.addWidget(rel_frame)
        # --- АЗАРТ (Часть C) ---
        ludo_frame = QFrame()
        lf = QVBoxLayout(ludo_frame)
        lt = QLabel("🎰 Азарт-слой (награды только за работу)")
        lt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        lf.addWidget(lt)
        self.chk_ludo = QCheckBox("Включить азарт-слой (сундуки, колесо, ставки)")
        self.chk_ludo.setToolTip("Выключено = все награды плоские, без рандома")
        lf.addWidget(self.chk_ludo)
        self.chk_wheel = QCheckBox("Колесо фортуны")
        lf.addWidget(self.chk_wheel)
        self.chk_wagers = QCheckBox("Ставки XP на задачи")
        lf.addWidget(self.chk_wagers)
        lrow = QHBoxLayout()
        lrow.addWidget(QLabel("Лимит спинов в день:"))
        self.spin_wheel_limit = QSpinBox()
        self.spin_wheel_limit.setRange(1, 50)
        lrow.addWidget(self.spin_wheel_limit)
        lrow.addStretch()
        lf.addLayout(lrow)
        self.lbl_odds = QLabel("")
        self.lbl_odds.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        self.lbl_odds.setWordWrap(True)
        lf.addWidget(self.lbl_odds)
        btn_save_ludo = QPushButton("💾 Сохранить азарт")
        btn_save_ludo.setStyleSheet("background-color: #533483; font-weight: bold;")
        btn_save_ludo.clicked.connect(self._save_ludo)
        lf.addWidget(btn_save_ludo)
        layout.addWidget(ludo_frame)
        # --- СПРАЙТЫ ---
        spr_frame = QFrame()
        sf = QVBoxLayout(spr_frame)
        st = QLabel("🖼 Спрайты аватара")
        st.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        sf.addWidget(st)
        for em in self.avatar.emotions:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            name = QLabel(EMOTIONS_RU[em])
            name.setFixedWidth(130)
            name.setStyleSheet("background: transparent;")
            hl.addWidget(name)
            prev = QLabel()
            prev.setFixedSize(44, 44)
            prev.setStyleSheet("background: #0f3460; border-radius: 6px;")
            prev.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.previews[em] = prev
            hl.addWidget(prev)
            btn_pick = QPushButton("Выбрать...")
            btn_pick.clicked.connect(lambda _, e=em: self._pick(e))
            hl.addWidget(btn_pick)
            btn_del = QPushButton("✖")
            btn_del.setFixedWidth(40)
            btn_del.clicked.connect(lambda _, e=em: self._remove_sprite(e))
            hl.addWidget(btn_del)
            hl.addStretch()
            sf.addWidget(row)
        btn_folder = QPushButton("📂 Открыть папку спрайтов")
        btn_folder.clicked.connect(self._open_folder)
        sf.addWidget(btn_folder)
        layout.addWidget(spr_frame)
        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def sync(self):
        m = self.monitor
        self.chk_monitor.setChecked(m.enabled)
        self.chk_push.setChecked(m.push_enabled)
        self.chk_voice.setChecked(m.voice_enabled)
        self.spin_compliance.setValue(m.compliance)
        self.spin_grace.setValue(m.remind_every)
        self.spin_cheer.setValue(m.cheer_every)
        self.spin_remind.setValue(m.grace)
        self.edit_distract.setText(", ".join(m.distract))
        self.edit_work.setText(", ".join(m.work))
        self.engine_combo.setCurrentIndex(1 if self.voice.engine == "gemini" else 0)
        self.key_edit.setText(self.voice.gemini_key)
        self.proxy_edit.setText(getattr(self.voice, "gemini_proxy", ""))
        idx = GEMINI_VOICES.index(self.voice.gemini_voice) if self.voice.gemini_voice in GEMINI_VOICES else 0
        self.gvoice_combo.setCurrentIndex(idx)
        self.chk_emotion.setChecked(self.voice.emotion_fx)
        if self.voice.voice_id == "ru-RU-DmitryNeural":
            self.voice_combo.setCurrentIndex(1)
        elif self.voice.voice_id is None:
            self.voice_combo.setCurrentIndex(2)
        else:
            self.voice_combo.setCurrentIndex(0)
        self.pitch_slider.setValue(self.voice.pitch_hz)
        self.rate_slider.setValue(self.voice.rate_extra)
        self._update_voice_labels()
        self._load_style_event()
        self._load_phrase_event()
        self._refresh_previews()
        self._sync_relationship()

    def _sync_relationship(self):
        """Часть B: заполнить секцию «Отношения» из Mood/rituals/seasons."""
        mood = getattr(self, "mood", None)
        if mood is None:
            return
        self.spin_ignore_threshold.setValue(mood.threshold())
        self.spin_praise_cooldown.setValue(mood.praise_cooldown_sec() // 60)
        self.spin_ritual_hour.setValue(self.rituals.data["ritual_hour"])
        self.spin_ritual_min.setValue(self.rituals.data["ritual_minute"])
        s = self.seasons.current()
        rate = int(self.rituals.ignore_rate_7d() * 100)
        self.lbl_season.setText(f"Текущий сезон: {s['emoji']} {s['name']} · доля игнора за 7 дней: {rate}%")
        if self.chests is not None:
            self._sync_ludo()

    def _sync_ludo(self):
        """Часть C: открытые вероятности и pity (этический ограничитель №2)."""
        self.chk_ludo.setChecked(self.chests.enabled() and self.wheel.enabled() and self.wagers.enabled())
        self.chk_wheel.setChecked(self.wheel.enabled())
        self.chk_wagers.setChecked(self.wagers.enabled())
        self.spin_wheel_limit.setValue(self.wheel.data.get("wheel_daily_limit", 5))
        p = self.chests.pity_info()
        self.lbl_odds.setText(
            "Вероятности сундуков: common 60% · rare 25% · epic 12% · legendary 3%  |  "
            f"Pity: epic+ каждые {p['pity_epic']} (сейчас {p['since_epic']}), "
            f"legendary каждые {p['pity_legendary']} (сейчас {p['since_legendary']})")

    def _save_ludo(self):
        on = self.chk_ludo.isChecked()
        self.chests.set_enabled(on)
        self.wheel.set_enabled(on and self.chk_wheel.isChecked())
        self.wagers.set_enabled(on and self.chk_wagers.isChecked())
        self.wheel.data["wheel_daily_limit"] = self.spin_wheel_limit.value()
        self.wheel.save()
        self.companion.say("happy", self.bank.say("settings_saved"))

    def _save_relationship(self):
        self.mood.data["mood_ignore_threshold"] = self.spin_ignore_threshold.value()
        self.mood.data["mood_praise_cooldown_min"] = self.spin_praise_cooldown.value()
        self.mood.save()
        self.rituals.set_time(self.spin_ritual_hour.value(), self.spin_ritual_min.value())
        self.companion.say("happy", self.bank.say("settings_saved"))

    def _load_style_event(self):
        key = self.style_combo.currentData()
        self.style_edit.setPlainText(self.voice.styles.get(key, STYLE_PROMPTS.get(key, "")))

    def _save_style(self):
        key = self.style_combo.currentData()
        self.voice.styles[key] = self.style_edit.toPlainText().strip()
        self.voice.set_styles(self.voice.styles)
        self.companion.say("happy", self.bank.say("settings_saved"))

    def _reset_style(self):
        self.voice.styles = dict(STYLE_PROMPTS)
        self.voice.set_styles(self.voice.styles)
        self._load_style_event()

    def _load_phrase_event(self):
        key = self.phr_combo.currentData()
        lines = self.bank.data.get(key) or DEFAULT_PHRASES.get(key) or []
        self.phr_edit.setPlainText("\n".join(lines))

    def _save_phrases(self):
        key = self.phr_combo.currentData()
        lines = [l.strip() for l in self.phr_edit.toPlainText().split("\n") if l.strip()]
        if lines:
            self.bank.data[key] = lines
            self.bank.save()
            self.companion.say("happy", self.bank.say("settings_saved"))

    def _reset_phrases(self):
        self.bank.reset()
        self._load_phrase_event()

    def _refresh_previews(self):
        emojis = {"neutral": "😐", "happy": "😊", "worried": "😟",
                  "sarcastic": "😏", "excited": "🤩", "caring": "💜"}
        for em, prev in self.previews.items():
            pix = self.avatar.pixmap_for(em, 40)
            if pix:
                prev.setPixmap(pix)
                prev.setText("")
            else:
                prev.clear()
                prev.setText(emojis[em])

    def _save_monitor(self):
        self.monitor.apply_settings(
            self.chk_monitor.isChecked(), self.chk_push.isChecked(),
            self.chk_voice.isChecked(), self.spin_remind.value(),
            self.spin_grace.value(), self.spin_compliance.value(),
            self.spin_cheer.value(),
            [s.strip().lower() for s in self.edit_distract.text().split(",") if s.strip()],
            [s.strip().lower() for s in self.edit_work.text().split(",") if s.strip()])
        self.companion.say("happy", self.bank.say("settings_saved"))

    def _apply_preset(self, voice_idx, pitch, rate):
        self.voice_combo.setCurrentIndex(voice_idx)
        self.pitch_slider.setValue(pitch)
        self.rate_slider.setValue(rate)

    def _update_voice_labels(self):
        self.pitch_label.setText(f"{self.pitch_slider.value():+d} Hz")
        self.rate_label.setText(f"{self.rate_slider.value():+d}%")

    def _current_voice_id(self):
        idx = self.voice_combo.currentIndex()
        if idx == 0:
            return "ru-RU-SvetlanaNeural"
        if idx == 1:
            return "ru-RU-DmitryNeural"
        return None

    def _show_voice_error(self, text):
        if text:
            self.voice_error_label.setText(text)
            self.voice_error_label.show()
        else:
            self.voice_error_label.hide()

    def _test_voice(self):
        self.voice.clear()
        self._show_voice_error("")
        self.voice.speak("Привет~ Я Кай. Ну как тебе мой голос, м?.. 💋",
                         block=False, emotion="caring")

    def _test_gemini(self):
        """Живой тест Gemini TTS: генерация в фоне + понятная ошибка, если недоступен."""
        self._show_voice_error("")
        self.voice.clear()
        key = self.key_edit.text().strip()
        if not key:
            self._show_voice_error("Вставь API-ключ Gemini (AIza...) — без ключа Gemini не работает.")
            return
        btn = self.sender()
        self._gemini_test_btn = btn
        btn.setEnabled(False)
        btn.setText("⏳ Генерирую...")
        proxy = self.proxy_edit.text().strip()
        phrase = self.bank.say("greet")

        def worker():
            # Временный клиент с ключевом/прокси из формы — настройки не сохраняем
            engine = self.voice
            saved = (engine.gemini_key, engine.gemini_voice, engine.gemini_proxy,
                     engine.gemini_proxy_verify, engine._gclient)
            engine.gemini_key = key
            engine.gemini_proxy = proxy
            engine._gclient = None
            try:
                path = engine.gemini_provider.render("Скажи по-русски. Текст: " + phrase, "caring")
                engine._play_file(path)
                done = (None,)
            except Exception as e:
                err = str(e)
                if "location is not supported" in err:
                    err = ("Gemini API недоступен из твоего региона (User location is not supported).\n"
                           "Впиши прокси в поле выше (например http://127.0.0.1:8080), нажми «💾 Применить голос» и попробуй снова.")
                elif "RESOURCE_EXHAUSTED" in err or "429" in err:
                    import re as _re
                    if "PerDay" in err:
                        err = ("Дневной лимит Gemini TTS исчерпан (бесплатный тариф).\n"
                               "Квота обновляется около 10:00 по Москве. Либо подключи биллинг в Google AI Studio.")
                    else:
                        wait = ""
                        m = _re.search(r"retry in ([\d.]+)s", err)
                        if m:
                            wait = f" (попробуй через ~{int(float(m.group(1))) + 2} сек)"
                        err = ("Минутный лимит Gemini исчерпан: на бесплатном тарифе TTS — 10 запросов в минуту." + wait +
                               "\nПодожди немного и нажми «✨ Тест Gemini» ещё раз.")
                elif "API key not valid" in err or "API_KEY_INVALID" in err:
                    err = "Ключ Gemini отклонён (API key not valid). Проверь ключ в aistudio.google.com."
                done = (err,)
            finally:
                (engine.gemini_key, engine.gemini_voice, engine.gemini_proxy,
                 engine.gemini_proxy_verify, engine._gclient) = saved
            self._gemini_test_done.emit(done)

        threading.Thread(target=worker, daemon=True).start()

    def _on_gemini_test_done(self, res):
        btn = self._gemini_test_btn
        if btn:
            btn.setEnabled(True)
            btn.setText("✨ Тест Gemini")
        self._show_voice_error(res[0] if res else None)

    def _save_voice(self):
        self.voice.set_config(
            "gemini" if self.engine_combo.currentIndex() == 1 else "edge",
            self.key_edit.text(),
            self.gvoice_combo.currentText(),
            self._current_voice_id(),
            self.pitch_slider.value(),
            self.rate_slider.value(),
            gemini_proxy=self.proxy_edit.text())
        self._show_voice_error("")
        self.voice.speak(self.bank.say("voice_saved"), block=False, emotion="caring")

    def _pick(self, emotion):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Спрайт для эмоции «{EMOTIONS_RU[emotion]}»", "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp)")
        if path:
            self.avatar.set_from_file(emotion, path)
            self._refresh_previews()
            self.avatar_changed.emit()

    def _remove_sprite(self, emotion):
        self.avatar.remove(emotion)
        self._refresh_previews()
        self.avatar_changed.emit()

    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.avatar.dir)))
