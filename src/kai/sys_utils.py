"""
sys_utils — системные хелперы (краш-хук, заголовок активного окна, пуши).
Владельцы: _crash_hook, get_foreground_title, push_notify.
Зависимости: sys, os, ctypes, traceback, pathlib; plyer (ленивый импорт).
"""
import sys
import os
import ctypes
import traceback
from pathlib import Path


def _crash_hook(exc_type, exc_value, tb):
    msg = "".join(traceback.format_exception(exc_type, exc_value, tb))
    print("CRASH:\n", msg)
    try:
        log = Path.home() / "AppData" / "Roaming" / "pixel" / "crash.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(msg + "\n=====\n")
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, tb)


def setup_crash_hook():
    """Ставит _crash_hook как sys.excepthook (в монолите — присваивание при импорте)."""
    sys.excepthook = _crash_hook


def get_foreground_title():
    try:
        if os.name != "nt":
            return ""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    except Exception:
        return ""


def push_notify(title, message):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=6, app_name="Kai")
    except Exception:
        pass
