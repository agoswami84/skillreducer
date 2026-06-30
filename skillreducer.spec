# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — build standalone skillreducer binary."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
root = Path(SPECPATH)

hiddenimports = [
    "agno",
    "agno.agent",
    "agno.models",
    "agno.models.openai",
    "agno.models.openai.chat",
    "agno.run.agent",
    "tiktoken",
    "tiktoken_ext.openai_public",
    "click",
    "yaml",
    "rich",
    "openai",
]

datas = [
    *collect_data_files("tiktoken"),
    *collect_data_files("tiktoken_ext"),
]

a = Analysis(
    [str(root / "skillreducer" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="skillreducer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
