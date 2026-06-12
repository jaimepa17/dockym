from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "dockym"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_PATHS = [
    str(Path.home() / "Documentos"),
]

PANEL_POSITIONS = ("right", "left", "bottom")
THEMES = ("dark", "dark_vscode", "dark_claude", "light")
FONTS = (
    "Inter", "Segoe UI", "SF Pro", "Roboto", "Ubuntu",
    "Fira Code", "JetBrains Mono", "Cascadia Code",
    "Source Code Pro", "IBM Plex Mono", "Hack", "Menlo",
)


@dataclass
class Config:
    paths: list[str] = field(default_factory=lambda: DEFAULT_PATHS.copy())
    active_profile: str = "dev"
    refresh_interval: int = 5
    minimize_to_tray: bool = True
    # Appearance
    panel_position: str = "right"  # "right" | "left" | "bottom"
    theme: str = "dark"            # "dark" | "dark_vscode" | "dark_claude" | "light"
    font_family: str = "Inter"

    @classmethod
    def load(cls) -> Config:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                # BUG-012: filter unknown keys to prevent data loss
                valid = {f.name for f in fields(Config)}
                data = {k: v for k, v in data.items() if k in valid}
                if data.get("panel_position") not in PANEL_POSITIONS:
                    data["panel_position"] = "right"
                if data.get("theme") not in THEMES:
                    data["theme"] = "dark"
                if data.get("font_family") not in FONTS:
                    data["font_family"] = "Inter"
                return cls(**data)
            except (json.JSONDecodeError, TypeError, KeyError):
                return cls()
        return cls()

    def save(self) -> None:
        """Atomically write config: write to temp file then os.replace()."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(asdict(self), f, indent=2)
            os.replace(tmp_path, CONFIG_FILE)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def add_path(self, path: str) -> None:
        if path not in self.paths:
            self.paths.append(path)
            self.save()

    def remove_path(self, path: str) -> None:
        if path in self.paths:
            self.paths.remove(path)
            self.save()
