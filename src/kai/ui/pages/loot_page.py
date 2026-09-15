"""
ui.pages.loot_page — вкладка «🎰 Сокровищница»: инвентарь, коллекция, колесо
(анимация стрелки), история дропов, открытая таблица вероятностей.
Владельцы: LootPage. Анимация — QTimer/QPropertyAnimation в главном потоке.
Зависимости: PyQt6; core.economy/economy, core.loot.ChestEngine, core.wheel.WheelFortune,
core.collections.MoodCollection; kai.core.loot.RARITY_TABLE/PITY.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFrame, QListWidget, QScrollArea, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QTransform

from kai.core.loot import RARITY_TABLE, PITY_EPIC, PITY_LEGENDARY
from kai.core.collections import CARD_NAMES


class LootPage(QWidget):
    """Сокровищница: спин через wheel-объект, награды — через сигналы движков."""

    def __init__(self, wallet, chests, wheel, collection, parent=None):
        super().__init__()
        self.wallet = wallet
        self.chests = chests
        self.wheel = wheel
        self.collection = collection
        self._arrow_angle = 0
        self._init_ui()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(30, 20, 30, 20)
        outer.setSpacing(15)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        title = QLabel("🎰 Сокровищница Кая")
        title.setStyleSheet("font-size: 26px; font-weight: bold; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        # --- КОШЕЛЁК ---
        self.wallet_label = QLabel("")
        self.wallet_label.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent;")
        self.wallet_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wallet_label)
        # --- КОЛЕСО ---
        wheel_frame = QFrame()
        wf = QVBoxLayout(wheel_frame)
        wt = QLabel("🎡 Колесо фортуны")
        wt.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        wf.addWidget(wt)
        self.wheel_view = QLabel("🎯")
        self.wheel_view.setStyleSheet("font-size: 64px; background: transparent;")
        self.wheel_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wf.addWidget(self.wheel_view)
        self.charge_label = QLabel("")
        self.charge_label.setStyleSheet("color: #888; font-size: 12px; background: transparent;")
        self.charge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wf.addWidget(self.charge_label)
        self.btn_spin = QPushButton("🎰 Крутить (50 монет)")
        self.btn_spin.clicked.connect(self._spin)
        wf.addWidget(self.btn_spin)
        self.wheel_result = QLabel("")
        self.wheel_result.setWordWrap(True)
        self.wheel_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wheel_result.setStyleSheet("font-size: 14px; background: transparent;")
        wf.addWidget(self.wheel_result)
        layout.addWidget(wheel_frame)
        # --- КОЛЛЕКЦИЯ ---
        col_frame = QFrame()
        cf = QVBoxLayout(col_frame)
        ct = QLabel("🃏 Коллекция «Настроения Кая» (12 карт)")
        ct.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        cf.addWidget(ct)
        self.cards_label = QLabel("")
        self.cards_label.setWordWrap(True)
        self.cards_label.setStyleSheet("font-size: 13px; background: transparent;")
        cf.addWidget(self.cards_label)
        self.set_bonus_label = QLabel("")
        self.set_bonus_label.setStyleSheet("color: #ffd54f; font-size: 12px; background: transparent;")
        cf.addWidget(self.set_bonus_label)
        layout.addWidget(col_frame)
        # --- ИСТОРИЯ ---
        hist_frame = QFrame()
        hf = QVBoxLayout(hist_frame)
        ht = QLabel("📜 История дропов")
        ht.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        hf.addWidget(ht)
        self.hist_list = QListWidget()
        self.hist_list.setMaximumHeight(180)
        hf.addWidget(self.hist_list)
        layout.addWidget(hist_frame)
        # --- ОТКРЫТЫЕ ВЕРОЯТНОСТИ (этический ограничитель №2) ---
        odds_frame = QFrame()
        of = QVBoxLayout(odds_frame)
        ot = QLabel("📊 Вероятности (открыто, без обмана)")
        ot.setStyleSheet("font-size: 18px; font-weight: bold; background: transparent;")
        of.addWidget(ot)
        for name, w in RARITY_TABLE:
            total = sum(x for _, x in RARITY_TABLE)
            l = QLabel(f"• {name}: {w * 100 // total}%")
            l.setStyleSheet("font-size: 12px; background: transparent;")
            of.addWidget(l)
        self.pity_label = QLabel("")
        self.pity_label.setStyleSheet("font-size: 12px; color: #888; background: transparent;")
        of.addWidget(self.pity_label)
        layout.addWidget(odds_frame)
        layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def refresh(self):
        t = self.wallet.data["wallet"]["tokens"]
        self.wallet_label.setText(
            f"💰 {self.wallet.coins()} монет   ·   🔄 {t.get('reroll', 0)}"
            f"   🧊 {t.get('streak_freeze', 0)}   🕊 {t.get('debt_pardon', 0)}")
        cost_ok = self.wallet.coins() >= 50
        self.btn_spin.setEnabled(self.wheel.can_spin() or cost_ok and self.wheel.charges() > 0)
        self.btn_spin.setText(f"🎰 Крутить (заряды: {self.wheel.charges()}, лимит сегодня: {self.wheel.spins_left_today()})")
        owned = self.collection.owned()
        cards = "  ".join(f"[{CARD_NAMES[i - 1]}]" if i in owned else f"[{i} ❔]" for i in range(1, 13))
        self.cards_label.setText(cards or "пока пусто")
        if self.collection.complete():
            self.set_bonus_label.setText(f"👑 Сет собран! Титул + рамка + перманентно +5% XP (x{self.collection.bonus_multiplier():.2f})")
        else:
            self.set_bonus_label.setText(f"Собери все 12 → титул, рамка, +5% XP навсегда ({len(owned)}/12)")
        self.hist_list.clear()
        for h in self.chests.history()[:20]:
            mark = {"common": "📦", "rare": "💎", "epic": "🔥", "legendary": "👑"}.get(h["rarity"], "📦")
            self.hist_list.addItem(f"{mark} {h['rarity']} — {h.get('type', '?')}")
        p = self.chests.pity_info()
        self.pity_label.setText(
            f"Pity: epic+ гарантирован каждые {p['pity_epic']} сундуков (осталось {max(0, p['pity_epic'] - p['since_epic'])}), "
            f"legendary каждые {p['pity_legendary']} (осталось {max(0, p['pity_legendary'] - p['since_legendary'])})")

    # --- спин с анимацией стрелки ---
    def _spin(self):
        if not self.wheel.can_spin():
            self.wheel_result.setText("Нет зарядов или дневной лимит спинов исчерпан~")
            return
        if not self.wallet.spend_coins("wheel_spin"):
            self.wheel_result.setText("Нужно 50 монет~ Заработай их работой 😏")
            return
        self.btn_spin.setEnabled(False)
        self._anim = QPropertyAnimation(self, b"rotation")
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1440.0)
        self._anim.setDuration(1600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._finish_spin)
        self._anim.start()

    def _finish_spin(self):
        res = self.wheel.spin()
        self.btn_spin.setEnabled(True)
        if res is None:
            self.wheel_result.setText("Не сработало, м~")
            return
        if res["almost_jackpot"]:
            self.wheel_result.setText(f"🎯 Стрелка у самого джекпота! {res['label']} — почти!~")
        elif res["loot"].get("type") == "empty":
            self.wheel_result.setText("⬛ Пусто... Но работа твоя не пустая~")
        else:
            self.wheel_result.setText(f"🎉 {res['label']}!")
        self.refresh()

    def setRotation(self, angle):
        self._arrow_angle = angle
        self.wheel_view.setTransform(QTransform().rotate(angle))

    def rotation(self):
        return self._arrow_angle
