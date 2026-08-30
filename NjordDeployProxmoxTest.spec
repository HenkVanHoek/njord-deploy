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

from PyInstaller.utils.hooks import collect_data_files

stripe_datas = []
try:
    stripe_datas = collect_data_files('stripe') + collect_data_files('certifi')
except Exception:
    pass

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
    ] + stripe_datas,
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
        'scripts.proxmox_release_test_runner',
        'scripts.proxmox_backup_test_runner',
        'stripe',
        'managers',
        'managers.agent_manager',
        'managers.artifact_generator',
        'managers.backup_manager',
        'managers.billing_manager',
        'managers.component_manager',
        'managers.component_reader',
        'managers.component_writer',
        'managers.database_manager',
        'managers.deployment_evaluator',
        'managers.deployment_manager',
        'managers.setup_manager',
        'managers.ssh_manager',
        'managers.sync_manager',
        'src.managers',
        'src.managers.agent_manager',
        'src.managers.artifact_generator',
        'src.managers.backup_manager',
        'src.managers.billing_manager',
        'src.managers.component_manager',
        'src.managers.component_reader',
        'src.managers.component_writer',
        'src.managers.database_manager',
        'src.managers.deployment_evaluator',
        'src.managers.deployment_manager',
        'src.managers.setup_manager',
        'src.managers.ssh_manager',
        'src.managers.sync_manager',
        'utils',
        'utils.ai_failure_diagnoser',
        'utils.ai_generator',
        'utils.ai_generator_engine',
        'utils.ai_provider_manager',
        'utils.auth_utils',
        'utils.container_engine',
        'utils.dashy_updater',
        'utils.failed_components',
        'utils.frigate_camera_config_tool',
        'utils.generation_logger',
        'utils.proxmox_client',
        'utils.resource_utils',
        'utils.security_utils',
        'utils.ssh_utils',
        'utils.template_header',
        'src.utils',
        'src.utils.ai_failure_diagnoser',
        'src.utils.ai_generator',
        'src.utils.ai_generator_engine',
        'src.utils.ai_provider_manager',
        'src.utils.auth_utils',
        'src.utils.container_engine',
        'src.utils.dashy_updater',
        'src.utils.failed_components',
        'src.utils.frigate_camera_config_tool',
        'src.utils.generation_logger',
        'src.utils.proxmox_client',
        'src.utils.resource_utils',
        'src.utils.security_utils',
        'src.utils.ssh_utils',
        'src.utils.template_header',
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
