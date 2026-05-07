# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['abha_card_studio.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('tesseract', 'tesseract'), ('NotoSansTamil-Bold.ttf', '.'), ('background.jpg', '.'), ('background2.jpg', '.'), ('NotoSansMalayalam-Bold.ttf', '.'), ('NotoSansDevanagari-Bold.ttf', '.'), ('auto_updater.py', '.')],
    hiddenimports=['packaging'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='abha_card_studio',
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
    icon=['abha_studio.ico'],
)
