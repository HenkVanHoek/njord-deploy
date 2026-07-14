# NjordDeployInstaller.spec
import platform

# This file is a "blueprint" for PyInstaller, configured for a one-file,
# windowed application, consistent across all operating systems.

# Placeholders to prevent PyCharm unresolved reference warnings at design time
try:
    from PyInstaller.building.api import EXE, PYZ, Analysis
except ImportError:
    # noinspection PyUnusedLocal
    class Analysis:
        def __init__(self, *args, **kwargs):
            self.pure = None
            self.zipped_data = None
            self.scripts = None
            self.binaries = None
            self.zipfiles = None
            self.datas = None

    # noinspection PyUnusedLocal
    class PYZ:
        def __init__(self, *args, **kwargs):
            pass

    # noinspection PyUnusedLocal
    class EXE:
        def __init__(self, *args, **kwargs):
            pass


# --- Define the icon based on the OS ---
icon_file = None
if platform.system() == "Windows":
    icon_file = "images/favicon.ico"
elif platform.system() == "Darwin":  # Darwin is the system name for macOS
    # Activate the icon for macOS using the file you provided.
    icon_file = "images/njorddeploy-apple.icns"
# For other systems (like Linux), icon_file remains None.

a = Analysis(
    # Point to the correct main application script.
    ['src/configurator_app/app.py'],
    # Add 'src' to the path to help PyInstaller resolve local module imports.
    pathex=['src'],
    binaries=[],
    datas=[
        # Flask app templates and static files
        ('src/configurator_app/templates', 'templates'),
        ('src/configurator_app/static', 'static'),
        # Config files
        ('config', 'config'),
        # Component templates - essential for generating configurations
        ('component_templates', 'component_templates'),
        # Ansible playbooks and configuration files
        ('ansible', 'ansible'),
        # Documentation files
        ('docs', 'docs'),
        ('README.md', '.'),
        ('CONTRIBUTING.md', '.'),
        ('UTILITIES.md', '.'),
    ],
    hiddenimports=[
        'nacl',
        'bcrypt',
        'cryptography'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='NjordDeployInstaller',
    # --- CHANGE 1: Enable debug output from PyInstaller's bootloader ---
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # --- CHANGE 2: Enable the console to see tracebacks ---
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # This now uses the correct icon file for each OS.
    icon=icon_file
)
