"""
core.avatar — менеджер спрайтов аватара по эмоциям.
Владельцы: AvatarManager.
Зависимости: shutil, pathlib; PyQt6 (QPixmap, Qt).
"""
import shutil
from pathlib import Path

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from kai.constants import EMOTIONS_RU


class AvatarManager:
    def __init__(self, data_dir):
        self.dir = Path(data_dir) / "sprites"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.emotions = list(EMOTIONS_RU.keys())

    def path_for(self, emotion):
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            p = self.dir / f"{emotion}{ext}"
            if p.exists():
                return p
        return None

    def pixmap_for(self, emotion, size):
        p = self.path_for(emotion)
        if p:
            pix = QPixmap(str(p))
            if not pix.isNull():
                return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        return None

    def set_from_file(self, emotion, src_path):
        ext = Path(src_path).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            ext = ".png"
        dst = self.dir / f"{emotion}{ext}"
        for old in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            old_path = self.dir / f"{emotion}{old}"
            if old_path.exists() and old_path != dst:
                try:
                    old_path.unlink()
                except Exception:
                    pass
        shutil.copy2(src_path, dst)

    def remove(self, emotion):
        for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
            p = self.dir / f"{emotion}{ext}"
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass
