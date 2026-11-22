# -*- mode: python ; coding: utf-8 -*-
"""Compilation d'un exe Windows graphique et autonome (OCR intégré).

python -m PyInstaller windows/NombrePoints.spec --distpath dist
→ dist/NombrePoints.exe : double-clic, aucune installation requise.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("rapidocr_onnxruntime")
hidden = collect_submodules("rapidocr_onnxruntime") + [
    "rapidocr_onnxruntime.ch_ppocr_cls",
    "rapidocr_onnxruntime.ch_ppocr_det",
    "rapidocr_onnxruntime.ch_ppocr_rec",
    "rapidocr_onnxruntime.utils",
]

a = Analysis(
    ["../gui.py"],
    pathex=[".."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden + ["onnxruntime", "PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["easyocr"],
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
    console=False,
)
