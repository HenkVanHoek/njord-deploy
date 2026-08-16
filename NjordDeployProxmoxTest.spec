# NjordDeployProxmoxTest.spec
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
    ['run_proxmox_gui.py'],
    pathex=['src', '.'],
    binaries=[],
    datas=[
        ('scripts/templates', 'scripts/templates'),
        ('scripts/templates', 'templates'),
        ('scripts/static', 'scripts/static'),
        ('scripts/static', 'static'),
        ('scripts', 'scripts'),
        ('config', 'config'),
        ('component_templates', 'component_templates'),
        ('ansible', 'ansible'),
        ('docs', 'docs'),
        ('tests', 'tests'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'waitress',
        'nacl',
        'bcrypt',
        'cryptography',
        'dotenv',
        'flask',
        'requests',
        'yaml',
        'paramiko',
        'scripts.proxmox_gui',
        'scripts.proxmox_test_runner',
        'utils.proxmox_client',
        'utils.ai_failure_diagnoser',
        'utils.container_engine',
        'utils.failed_components',
        'managers.component_manager',
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
    name='NjordDeployProxmoxTest',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=icon_file
)
