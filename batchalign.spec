# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = []
datas += collect_data_files('torch')
datas += copy_metadata('torch')
datas += copy_metadata('tqdm')
datas += copy_metadata('transformers')
datas += copy_metadata('tokenizers')
datas += copy_metadata('regex')
datas += copy_metadata('requests')
datas += copy_metadata('packaging')
datas += copy_metadata('filelock')
datas += copy_metadata('numpy')
datas += copy_metadata('rev_ai')
datas += copy_metadata('montreal_forced_aligner')
datas += copy_metadata('textwrap3')

# librosa's needs
datas += [("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/python3.9/site-packages/librosa/util/example_data/*", "librosa/util/example_data")] 


block_cipher = None


a = Analysis(
    ['batchalign.py'],
    pathex=[],
    binaries=[ ("./ba/opt/textwrap3.py", '.'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libsndfile.dylib", '_soundfile_data'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libFLAC.8.dylib", '.'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libvorbis.0.4.9.dylib", '.'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libvorbisenc.2.0.12.dylib", '.'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libopus.0.dylib", '.'),
               ("/opt/homebrew/Caskroom/miniforge/base/envs/batchalign/lib/libogg.0.dylib", '.'),
               ("/usr/local/bin/praat2chat", '.'),
               ("/usr/local/bin/chat2praat", '.'),
               ("/usr/local/bin/chat2elan", '.'),
               ("/usr/local/bin/elan2chat", '.'),
               ("/usr/local/bin/flo", '.'),
               ("/usr/local/bin/kwal", '.'),
               ("/usr/local/bin/lowcase", '.')],
    datas=datas,
    hiddenimports=['torch',
                   'montreal_forced_aligner',
                   'textwrap3'],
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
    name='batchalign',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='batchalign',
)
