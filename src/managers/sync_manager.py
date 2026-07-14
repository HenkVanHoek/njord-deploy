# src/managers/sync_manager.py

import json
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests  # type: ignore
from appdirs import user_data_dir

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manages synchronization of components metadata and templates
    between a remote GitHub repository and the local application data directory.
    """

    def __init__(self, local_metadata_path: Path, local_templates_path: Path):
        self.local_metadata_path = local_metadata_path
        self.local_templates_path = local_templates_path

        app_data_dir = Path(user_data_dir("NjordDeploy", "NjordDeploy"))
        self.cache_dir = app_data_dir / "remote_components_cache"
        self.cache_metadata_path = self.cache_dir / "components_metadata.json"
        self.cache_templates_path = self.cache_dir / "component_templates"
        self.git_repo_dir = app_data_dir / "remote_components_git"

    def fetch_from_remote(self) -> bool:
        """
        Downloads the latest ZIP from GitHub and extracts it to the cache directory.
        Returns True if successful, False otherwise.
        """
        repo = os.environ.get(
            "PI_SELFHOSTING_COMPONENTS_REPO",
            "HenkVanHoek/njorddeploy-components",
        )
        branch = os.environ.get("PI_SELFHOSTING_COMPONENTS_BRANCH", "main")
        url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"

        try:
            logger.info(f"Fetching remote components from {url}")
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                logger.error(
                    f"Failed to download repository ZIP from {url}. "
                    f"Status code: {response.status_code}"
                )
                return False

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / "repo.zip"
                with open(zip_path, "wb") as f:
                    f.write(response.content)

                extract_path = Path(tmpdir) / "extracted"
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(extract_path)

                subdirs = [d for d in extract_path.iterdir() if d.is_dir()]
                if not subdirs:
                    logger.error("No subdirectory found in extracted ZIP archive")
                    return False

                repo_root = subdirs[0]

                # Ensure clean target cache directory
                if self.cache_dir.exists():
                    shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)

                remote_meta = repo_root / "components_metadata.json"
                remote_templates = repo_root / "component_templates"

                if remote_meta.exists():
                    shutil.copy2(remote_meta, self.cache_metadata_path)
                if remote_templates.exists():
                    shutil.copytree(remote_templates, self.cache_templates_path)

            logger.info("Successfully fetched and cached remote components")
            return True
        except Exception as e:
            logger.error(f"Error fetching remote components: {e}", exc_info=True)
            return False

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_local_component_meta(self, component_id: str) -> dict:
        data = self._load_json(self.local_metadata_path)
        return data.get("components", {}).get(component_id, {})

    def _get_remote_component_meta(self, component_id: str) -> dict:
        data = self._load_json(self.cache_metadata_path)
        return data.get("components", {}).get(component_id, {})

    def _local_component_exists(self, component_id: str) -> bool:
        data = self._load_json(self.local_metadata_path)
        return component_id in data.get("components", {})

    def _remote_component_exists(self, component_id: str) -> bool:
        data = self._load_json(self.cache_metadata_path)
        return component_id in data.get("components", {})

    def _compare_directories(self, dir1: Path, dir2: Path) -> bool:
        if not dir1.exists() or not dir2.exists():
            return False

        files1 = {f.relative_to(dir1) for f in dir1.rglob("*") if f.is_file()}
        files2 = {f.relative_to(dir2) for f in dir2.rglob("*") if f.is_file()}

        if files1 != files2:
            return False

        for rel_path in files1:
            f1 = dir1 / rel_path
            f2 = dir2 / rel_path
            try:
                # Normalize line endings and strip text files to prevent false positives
                if rel_path.suffix.lower() in (
                    ".yml",
                    ".yaml",
                    ".json",
                    ".conf",
                    ".rb",
                    ".txt",
                    ".sh",
                    ".template",
                ):
                    c1 = (
                        f1.read_text(encoding="utf-8", errors="ignore")
                        .replace("\r\n", "\n")
                        .strip()
                    )
                    c2 = (
                        f2.read_text(encoding="utf-8", errors="ignore")
                        .replace("\r\n", "\n")
                        .strip()
                    )
                    if c1 != c2:
                        return False
                else:
                    if f1.read_bytes() != f2.read_bytes():
                        return False
            except Exception:
                return False

        return True

    def compare_component(self, component_id: str) -> str:
        """
        Compares local and remote component files and metadata.
        Returns one of: 'synced', 'modified', 'local_only', 'remote_only'.
        """
        local_exists = self._local_component_exists(component_id)
        remote_exists = self._remote_component_exists(component_id)

        if local_exists and not remote_exists:
            return "local_only"
        if not local_exists and remote_exists:
            return "remote_only"
        if not local_exists and not remote_exists:
            return "not_found"

        # Compare metadata dicts
        local_meta = self._get_local_component_meta(component_id)
        remote_meta = self._get_remote_component_meta(component_id)
        if local_meta != remote_meta:
            return "modified"

        # Compare template directory
        local_dir = self.local_templates_path / component_id
        remote_dir = self.cache_templates_path / component_id

        if not self._compare_directories(local_dir, remote_dir):
            return "modified"

        return "synced"

    def get_sync_status(self) -> dict:
        """Returns status info for all components and remote cache status."""
        remote_fetched = self.cache_metadata_path.exists()

        local_data = self._load_json(self.local_metadata_path)
        remote_data = self._load_json(self.cache_metadata_path)

        local_comps = set(local_data.get("components", {}).keys())
        remote_comps = set(remote_data.get("components", {}).keys())

        all_comps = local_comps.union(remote_comps)
        status_dict = {}

        for comp_id in all_comps:
            status_dict[comp_id] = self.compare_component(comp_id)

        global_out_of_sync = False
        if remote_fetched:
            local_packages = local_data.get("packages", {})
            remote_packages = remote_data.get("packages", {})

            local_rules = local_data.get("_njorddeploy", {}).get("group_rules", {})
            remote_rules = remote_data.get("_njorddeploy", {}).get("group_rules", {})

            local_order = local_data.get("_njorddeploy", {}).get("group_order", [])
            remote_order = remote_data.get("_njorddeploy", {}).get("group_order", [])

            if (
                local_packages != remote_packages
                or local_rules != remote_rules
                or local_order != remote_order
            ):
                global_out_of_sync = True

        return {
            "remote_fetched": remote_fetched,
            "components": status_dict,
            "global_metadata_out_of_sync": global_out_of_sync,
        }

    def sync_component(self, component_id: str) -> bool:
        """
        Synchronizes a single component from the remote cache to the local files.
        """
        if not self.cache_metadata_path.exists():
            return False

        # 1. Update metadata
        local_data = self._load_json(self.local_metadata_path)
        remote_data = self._load_json(self.cache_metadata_path)

        remote_comp_meta = remote_data.get("components", {}).get(component_id)
        if remote_comp_meta:
            if "components" not in local_data:
                local_data["components"] = {}
            local_data["components"][component_id] = remote_comp_meta
        else:
            logger.warning(
                f"Component {component_id} does not exist on remote. "
                "Aborting sync to protect local files."
            )
            return False

        try:
            self.local_metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.local_metadata_path, "w", encoding="utf-8") as f:
                json.dump(local_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save local metadata during sync: {e}")
            return False

        # 2. Update templates folder
        local_dir = self.local_templates_path / component_id
        remote_dir = self.cache_templates_path / component_id

        try:
            if local_dir.exists():
                shutil.rmtree(local_dir)
            if remote_dir.exists():
                local_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(remote_dir, local_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to sync templates for {component_id}: {e}")
            return False

    def sync_all(self) -> bool:
        """
        Synchronizes all components from the remote cache to local.
        """
        if not self.cache_metadata_path.exists():
            return False

        try:
            self.local_metadata_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.cache_metadata_path, self.local_metadata_path)

            if self.local_templates_path.exists():
                shutil.rmtree(self.local_templates_path)
            if self.cache_templates_path.exists():
                shutil.copytree(self.cache_templates_path, self.local_templates_path)
            return True
        except Exception as e:
            logger.error(f"Failed to sync all components: {e}")
            return False

    def check_write_access(self) -> bool:
        """Verifies if the local environment has write access to the components repo."""
        import subprocess  # nosec B404

        try:
            self._prepare_git_repo()
            git_cwd = str(self.git_repo_dir)
        except Exception:
            # Find project git directory
            git_cwd = None
            start_path = self.local_metadata_path.parent
            for parent in [start_path] + list(start_path.parents):
                if (parent / ".git").exists():
                    git_cwd = str(parent)
                    break
            if not git_cwd:
                git_cwd = str(self.local_metadata_path.parent.parent)

        # Try SSH push dry run
        ssh_url = "git@github.com:HenkVanHoek/njorddeploy-components.git"
        try:
            res = subprocess.run(  # nosec B603 B607
                ["git", "push", "--dry-run", ssh_url],
                cwd=git_cwd,
                capture_output=True,
                text=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                timeout=10,
            )
            logger.info(
                f"SSH write access check result: code={res.returncode}, "
                f"stderr={res.stderr.strip()}"
            )
            if (
                res.returncode in (0, 1)
                and "denied" not in res.stderr.lower()
                and "fatal" not in res.stderr.lower()
            ):
                return True
        except Exception as e:
            logger.error(f"SSH write access check failed: {e}")

        # Try HTTPS push dry run
        https_url = "https://github.com/HenkVanHoek/njorddeploy-components.git"
        try:
            res = subprocess.run(  # nosec B603 B607
                ["git", "push", "--dry-run", https_url],
                cwd=git_cwd,
                capture_output=True,
                text=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                timeout=10,
            )
            logger.info(
                f"HTTPS write access check result: code={res.returncode}, "
                f"stderr={res.stderr.strip()}"
            )
            if (
                res.returncode in (0, 1)
                and "denied" not in res.stderr.lower()
                and "fatal" not in res.stderr.lower()
            ):
                return True
        except Exception as e:
            logger.error(f"HTTPS write access check failed: {e}")

        return False

    def _prepare_git_repo(self) -> str:
        """Clones or updates the local git cache for components repo."""
        self.git_repo_dir.parent.mkdir(parents=True, exist_ok=True)
        ssh_url = "git@github.com:HenkVanHoek/njorddeploy-components.git"
        https_url = "https://github.com/HenkVanHoek/njorddeploy-components.git"

        if self.git_repo_dir.exists() and (self.git_repo_dir / ".git").exists():
            import subprocess  # nosec B404

            res = subprocess.run(  # nosec B603 B607
                ["git", "pull"],
                cwd=str(self.git_repo_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                timeout=30,
            )
            if res.returncode == 0:
                return "existing"
            else:
                logger.warning(f"Git pull failed: {res.stderr}. Re-cloning...")
                shutil.rmtree(self.git_repo_dir)

        import subprocess  # nosec B404

        # Try cloning using SSH
        res = subprocess.run(  # nosec B603 B607
            ["git", "clone", ssh_url, str(self.git_repo_dir)],
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=60,
        )
        if res.returncode == 0:
            return ssh_url

        # Try cloning using HTTPS
        res = subprocess.run(  # nosec B603 B607
            ["git", "clone", https_url, str(self.git_repo_dir)],
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=60,
        )
        if res.returncode == 0:
            return https_url

        raise RuntimeError(f"Failed to clone components repository: {res.stderr}")

    def validate_metadata_header(self, component_id: str) -> bool:
        """Checks if the component template has the four metadata header comments."""
        filename = "docker-compose.template.yml"
        filepath = self.local_templates_path / component_id / filename
        if not filepath.exists():
            return False

        try:
            content = filepath.read_text(encoding="utf-8")
            lines = content.splitlines()
            found_fields = set()
            required = [
                "status:",
                "last_tested_version:",
                "platform_notes:",
                "breaking_changes:",
            ]

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    comment = stripped[1:].strip()
                    for field in required:
                        if comment.startswith(field):
                            found_fields.add(field)
                else:
                    break

            return len(found_fields) == len(required)
        except Exception:
            return False

    def upload_component(self, component_id: str) -> bool:
        """
        Commits and pushes the component templates and metadata
        to the remote repo.
        """
        # 1. Ensure git repo is ready
        self._prepare_git_repo()

        # 2. Copy component template folder
        src_dir = self.local_templates_path / component_id
        dest_dir = self.git_repo_dir / "component_templates" / component_id

        if not src_dir.exists():
            raise FileNotFoundError(f"Local template dir {src_dir} does not exist.")

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)

        # 3. Update components_metadata.json in the git repo
        local_data = self._load_json(self.local_metadata_path)
        remote_metadata_path = self.git_repo_dir / "components_metadata.json"
        remote_data = self._load_json(remote_metadata_path)

        if "components" not in remote_data:
            remote_data["components"] = {}

        if component_id in local_data.get("components", {}):
            remote_data["components"][component_id] = local_data["components"][
                component_id
            ]
            with open(remote_metadata_path, "w", encoding="utf-8") as f:
                json.dump(remote_data, f, indent=4)

        # 4. Check for changes before committing
        import subprocess  # nosec B404

        status_res = subprocess.run(  # nosec B603 B607
            ["git", "status", "--porcelain"],
            cwd=str(self.git_repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        if not status_res.stdout.strip():
            logger.info("No changes to commit for component %s", component_id)
            return True

        # 5. Git add, commit, and push
        subprocess.run(  # nosec B603 B607
            [
                "git",
                "add",
                "components_metadata.json",
                f"component_templates/{component_id}",
            ],
            cwd=str(self.git_repo_dir),
            check=True,
        )
        subprocess.run(  # nosec B603 B607
            ["git", "commit", "-m", f"chore(components): update {component_id}"],
            cwd=str(self.git_repo_dir),
            check=True,
        )
        push_res = subprocess.run(  # nosec B603 B607
            ["git", "push"],
            cwd=str(self.git_repo_dir),
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=60,
        )
        if push_res.returncode != 0:
            raise RuntimeError(f"Git push failed: {push_res.stderr}")

        return True

    def upload_all_components(self) -> bool:
        """Uploads all local templates and metadata to the remote repository in bulk."""
        # 1. Ensure git repo is ready
        self._prepare_git_repo()

        # 2. Pre-flight validation on ALL local components
        local_data = self._load_json(self.local_metadata_path)
        components = local_data.get("components", {})
        invalid_components = []
        for comp_id in components:
            if not self.validate_metadata_header(comp_id):
                invalid_components.append(comp_id)

        if invalid_components:
            invalid_str = ", ".join(invalid_components)
            raise ValueError(
                "Upload aborted: The following components have incomplete or "
                f"malformed metadata headers: {invalid_str}"
            )

        # 3. Copy templates folder
        dest_templates_dir = self.git_repo_dir / "component_templates"
        if dest_templates_dir.exists():
            shutil.rmtree(dest_templates_dir)
        shutil.copytree(self.local_templates_path, dest_templates_dir)

        # 4. Copy components_metadata.json
        shutil.copy2(
            self.local_metadata_path, self.git_repo_dir / "components_metadata.json"
        )

        # 5. Check for changes before committing
        import subprocess  # nosec B404

        status_res = subprocess.run(  # nosec B603 B607
            ["git", "status", "--porcelain"],
            cwd=str(self.git_repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        if not status_res.stdout.strip():
            logger.info("No changes to commit for bulk upload")
            return True

        # 6. Git commit and push
        subprocess.run(  # nosec B603 B607
            ["git", "add", "components_metadata.json", "component_templates/"],
            cwd=str(self.git_repo_dir),
            check=True,
        )
        subprocess.run(  # nosec B603 B607
            ["git", "commit", "-m", "chore(components): bulk update components"],
            cwd=str(self.git_repo_dir),
            check=True,
        )
        push_res = subprocess.run(  # nosec B603 B607
            ["git", "push"],
            cwd=str(self.git_repo_dir),
            capture_output=True,
            text=True,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=60,
        )
        if push_res.returncode != 0:
            raise RuntimeError(f"Git push failed: {push_res.stderr}")

        return True
