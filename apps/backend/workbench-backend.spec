# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


backend_dir = Path(SPECPATH)
pypdfium2_datas = collect_data_files("pypdfium2")
pypdfium2_binaries = collect_dynamic_libs("pypdfium2")

a = Analysis(
    ["desktop_backend.py"],
    pathex=[str(backend_dir)],
    binaries=pypdfium2_binaries,
    datas=[
        (
            str(backend_dir / "app" / "db" / "migrations" / "0001_initial_core.sql"),
            "app/db/migrations",
        ),
    ]
    + pypdfium2_datas,
    hiddenimports=collect_submodules("uvicorn") + collect_submodules("pypdfium2"),
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
    name="workbench-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="workbench-backend",
)
