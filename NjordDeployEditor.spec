# NjordDeployEditor.spec
import platform

# Placeholders to prevent PyCharm unresolved reference warnings at design time
if "Analysis" not in globals():
    # noinspection PyUnusedLocal
    class Analysis:
        def __init__(self, *args, **kwargs):
            self.pure = None
            self.zipped_data = None
            self.scripts = None
            self.binaries = None
            self.zipfiles = None
            self.datas = None

if "PYZ" not in globals():
    # noinspection PyUnusedLocal
    class PYZ:
        def __init__(self, *args, **kwargs):
            pass

if "EXE" not in globals():
    # noinspection PyUnusedLocal
    class EXE:
        def __init__(self, *args, **kwargs):
            pass


icon_file = None
if platform.system() == "Windows":
    icon_file = "images/favicon.ico"
elif platform.system() == "Darwin":
    icon_file = "images/njorddeploy-apple.icns"

a = Analysis(
    ['run_editor.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/editor_app/templates', 'templates'),
        ('src/editor_app/static', 'static'),
        ('config', 'config'),
        ('component_templates', 'component_templates'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'waitress',
        'nacl',
        'bcrypt',
        'cryptography',
        'src.editor_app.app'
    ],
    hookspath=[],
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
    name='NjordDeployEditor',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=icon_file
)
