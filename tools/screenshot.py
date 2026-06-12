#!/usr/bin/env python3
"""
Take screenshots of Dockym for the README.
Usage: uv run python tools/screenshot.py
"""

import os
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

from PySide6.QtWidgets import QApplication
from dockym.app import DockymApp
from dockym.ui.main_window import MainWindow

SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "screenshots"


def shot(widget, name, delay=1.0):
    path = SCREENSHOTS_DIR / name
    print(f"  [{name}] ", end="", flush=True)
    app = QApplication.instance()
    app.processEvents()
    time.sleep(delay)
    app.processEvents()
    pixmap = widget.grab()
    if pixmap.isNull():
        print("✗ grab() returned null")
        return
    pixmap.save(str(path))
    size = os.path.getsize(path)
    print(f"✓ ({size // 1024} KB)")


def main():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    app = DockymApp(sys.argv)

    print("Creating main window...")
    window = MainWindow()
    window.resize(1200, 800)
    window.show()
    app.processEvents()
    time.sleep(2)
    app.processEvents()

    # Main window
    print("\n[1/5] Main window...")
    shot(window, "main-window.png", delay=1)

    # Command palette
    print("\n[2/5] Command palette...")
    palette = getattr(window, "_command_palette", None)
    if palette:
        try:
            palette.show_palette()
            app.processEvents()
            time.sleep(0.3)
            app.processEvents()
            shot(window, "command-palette.png", delay=0.3)
            palette.close()
        except Exception as e:
            print(f"  skipped ({e})")

    # Settings dialog
    print("\n[3/5] Settings dialog...")
    try:
        from dockym.ui.settings_dialog import SettingsDialog
        from dockym.models.config import Config
        dlg = SettingsDialog(config=Config.load(), parent=window)
        dlg.show()
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()
        shot(dlg, "settings-dialog.png", delay=0.3)
        dlg.close()
    except Exception as e:
        print(f"  skipped ({e})")

    # Appearance dialog
    print("\n[4/5] Appearance dialog...")
    try:
        from dockym.ui.appearance_dialog import AppearanceDialog
        from dockym.models.config import Config
        dlg = AppearanceDialog(config=Config.load(), parent=window)
        dlg.show()
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()
        shot(dlg, "appearance-dialog.png", delay=0.3)
        dlg.close()
    except Exception as e:
        print(f"  skipped ({e})")

    # Prune dialog
    print("\n[5/5] Prune dialog...")
    try:
        from dockym.ui.prune_dialog import PruneDialog
        dlg = PruneDialog(parent=window)
        dlg.show()
        app.processEvents()
        time.sleep(0.5)
        app.processEvents()
        shot(dlg, "prune-dialog.png", delay=0.3)
        dlg.close()
    except Exception as e:
        print(f"  skipped ({e})")

    print(f"\n✅ Done! Screenshots in: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    main()
