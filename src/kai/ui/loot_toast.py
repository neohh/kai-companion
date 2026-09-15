"""
ui.loot_toast — вскрытие сундука: задержка 0.8 c, цвет редкости, shake для legendary.
Владельцы: LootToast (сигнал revealed).
Зависимости: PyQt6. Near-miss дразнилка для колеса — через тот же тост.
"""
from PyQt6.QtWidgets import QVBoxLayout, QFrame, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint

from kai.ui.widgets import Toast

RARITY_STYLE = {
    "common": ("📦 Обычный сундук", "#eaeaea"),
    "rare": ("💎 Редкий сундук!", "#4fc3f7"),
    "epic": ("🔥 ЭПИЧЕСКИЙ сундук!", "#ba68c8"),
    "legendary": ("👑 ЛЕГЕНДАРНЫЙ СУНДУК!!!", "#ffd54f"),
}


def loot_text(loot):
    t = loot.get("type")
    if t == "coins":
        return f"💰 +{loot['amount']} монет"
    if t == "token":
        names = {"reroll": "🔄 реролл", "streak_freeze": "🧊 стрик-фриз", "debt_pardon": "🕊 прощение долга"}
        return f"Токен: {names.get(loot.get('token'), loot.get('token'))}"
    if t == "xp_mult":
        return f"✨ XP x{loot['multiplier']} на следующую задачу"
    if t == "cosmetic":
        return f"🎀 {loot['name']}"
    if t == "grace":
        return "🕊 Благодать Кая: долг списан"
    if t == "card":
        return "🃏 Карта коллекции!"
    return "🎁 Нечто"


class LootToast(Toast):
    revealed = pyqtSignal()

    def __init__(self, rarity, loot, near_miss_label=None):
        if near_miss_label:
            # дразнилка колеса: «почти джекпот»
            super().__init__("🎰 Колесо", near_miss_label)
            self._title_color("#ffd54f")
        else:
            title, color = RARITY_STYLE.get(rarity, RARITY_STYLE["common"])
            super().__init__(title, loot_text(loot))
            self._title_color(color)
        self.setFixedWidth(340)
        # задержка вскрытия 0.8 c: сперва «...»
        self._pending = True
        QTimer.singleShot(800, self._reveal)
        if rarity == "legendary" and not near_miss_label:
            QTimer.singleShot(820, self._shake)

    def _title_color(self, color):
        layout = self.layout()
        frame = layout.itemAt(0).widget()
        t = frame.layout().itemAt(0).widget()
        t.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {color}; background: transparent;")

    def _reveal(self):
        self._pending = False
        self.revealed.emit()

    def _shake(self):
        base = self.pos()
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(450)
        anim.setEasingCurve(QEasingCurve.Type.OutBounce)
        anim.setStartValue(base)
        anim.setKeyValueAt(0.15, base + QPoint(-7, 0))
        anim.setKeyValueAt(0.3, base + QPoint(7, 0))
        anim.setKeyValueAt(0.45, base + QPoint(-5, 0))
        anim.setKeyValueAt(0.6, base + QPoint(5, 0))
        anim.setKeyValueAt(0.75, base + QPoint(-3, 0))
        anim.setEndValue(base)
        anim.start()
        self._anim = anim  # держим ссылку
