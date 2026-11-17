# PyInstaller spec for Windows packaging of ngfw-appdetector.
# Build this on Windows. Cross-building a reliable Windows .exe from macOS is not supported.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

PROJECT_ROOT = Path.cwd()
ENTRYPOINT = PROJECT_ROOT / 'packaging' / 'pyi_entrypoint.py'
SOURCE_ROOT = PROJECT_ROOT / 'src'


a = Analysis(
    [str(ENTRYPOINT)],
    pathex=[str(SOURCE_ROOT)],
    binaries=[],
    datas=collect_data_files(
        'ngfw_appdetector',
        includes=[
            'lua_generator/templates/*.lua.j2',
            'web/templates/*.html',
            'web/static/app.css',
            'web/static/app.js',
            'web/static/htmx.min.js',
            'web/static/htmx.LICENSE',
        ],
    ),
    hiddenimports=['uvicorn', 'uvicorn.logging', 'uvicorn.loops.auto', 'uvicorn.protocols.http.auto'],
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
    [],
    exclude_binaries=True,
    name='ngfw-appdetector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ngfw-appdetector',
)
