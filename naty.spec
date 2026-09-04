# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('pystray') + collect_submodules('ddgs')

a = Analysis(['main.py'], pathex=[], binaries=[], datas=[('config.toml', '.')], hiddenimports=hiddenimports,
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['torch', 'tensorflow'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Naty', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=True, console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch=None, codesign_identity=None, entitlements_file=None, icon=None)
