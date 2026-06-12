# -*- mode: python ; coding: utf-8 -*-

import os
import re
import sys
from pathlib import Path

# PyInstaller does not define __file__ in the spec execution context,
# so we use the working directory (always the project root in CI).
PROJECT_ROOT = Path.cwd()
SRC_DIR = PROJECT_ROOT / "src"

# Read version from pyproject.toml so it stays in a single source of truth
_pyproject = (PROJECT_ROOT / "pyproject.toml").read_text()
_match = re.search(r'^version = "([^"]+)"', _pyproject, re.MULTILINE)
APP_VERSION = _match.group(1) if _match else "0.1.0"

a = Analysis(
    [str(SRC_DIR / "dockym" / "__init__.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        (str(SRC_DIR / "dockym" / "ui"), "dockym/ui"),
    ],
    hiddenimports=[
        "dockym",
        "dockym.app",
        "dockym.models",
        "dockym.models.config",
        "dockym.models.project",
        "dockym.engine",
        "dockym.engine.client",
        "dockym.engine.compose",
        "dockym.engine.scanner",
        "dockym.ui",
        "dockym.ui.main_window",
        "dockym.ui.project_tree",
        "dockym.ui.service_table",
        "dockym.ui.action_panel",
        "dockym.ui.settings_dialog",
        "dockym.ui.logs_dialog",
        "dockym.ui.env_dialog",
        "dockym.ui.exec_dialog",
        "dockym.ui.tray_manager",
        "dockym.ui.theme",
        "dockym.workers",
        "dockym.workers.docker_worker",
        "docker",
        "docker.transport",
        "docker.transport.basehttpadapter",
        "docker.transport.npipeconn",
        "docker.transport.npipesocket",
        "docker.transport.sshconn",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Dockym",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="Dockym.app",
        icon=None,
        bundle_identifier="com.dockym.app",
        info_plist={
            "CFBundleShortVersionString": APP_VERSION,
            "CFBundleVersion": APP_VERSION,
            "CFBundleName": "Dockym",
        },
    )
