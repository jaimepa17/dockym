from __future__ import annotations

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal, QObject


class TrayManager(QObject):
    show_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._default_icon())
        self._tray.setToolTip("Dockym — Docker Manager")
        self._setup_menu()
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _default_icon(self):
        return QIcon.fromTheme("docker",
                               QIcon.fromTheme("system-run",
                                               QIcon.fromTheme("computer")))

    def _setup_menu(self):
        menu = QMenu()
        show_action = menu.addAction("Mostrar Dockym")
        show_action.triggered.connect(self.show_requested.emit)
        menu.addSeparator()
        quit_action = menu.addAction("Salir")
        quit_action.triggered.connect(self.quit_requested.emit)
        self._tray.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_requested.emit()

    def set_icon(self, icon: QIcon):
        self._tray.setIcon(icon)

    def set_tooltip(self, text: str):
        self._tray.setToolTip(text)

    def show_message(self, title: str, message: str, icon=QSystemTrayIcon.MessageIcon.Information, duration: int = 3000):
        self._tray.showMessage(title, message, icon, duration)

    def hide(self):
        if self._tray is not None:
            self._tray.setVisible(False)
