# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['abha_card_studio.py'],
    pathex=[],
    binaries=[],
    datas=[('logo.png', '.'), ('tesseract', 'tesseract'), ('NotoSansTamil-Bold.ttf', '.'), ('background.jpg', '.'), ('background2.jpg', '.'), ('NotoSansMalayalam-Bold.ttf', '.'), ('NotoSansMalayalam-Bold.ttf', '.'), ('NotoSansDevanagari-Bold.ttf', '.')],
    hiddenimports=[],
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
    [],
    exclude_binaries=True,
    name='abha_card_studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['abha_studio.ico','logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='abha_card_studio',
)
