# -*- mode: python ; coding: utf-8 -*-
"""Compilation d'un exe autonome : pyinstaller windows/NombrePoints.spec"""

a = Analysis(
    ["../main.py"],
    pathex=[".."],
    binaries=[],
    datas=[],
    hiddenimports=["pytesseract", "PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NombrePoints",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
