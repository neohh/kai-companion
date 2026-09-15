"""
kai.__main__ — точка входа `python -m kai` (и консольный скрипт `kai`).
Зависимости: sys; PyQt6; kai.sys_utils; kai.ui.main_window.MainWindow.
"""
import sys

from PyQt6.QtWidgets import QApplication

from kai.sys_utils import setup_crash_hook


def main():
    setup_crash_hook()
    app = QApplication(sys.argv)
    app.setApplicationName("Kai")
    app.setQuitOnLastWindowClosed(False)
    from kai.ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
