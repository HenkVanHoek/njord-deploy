# src/managers/sync_manager.py

import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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
        self.is_offline = False

    @staticmethod
    def get_repo_config() -> dict[str, Any]:
        """Returns the active components repository configuration."""
        repo = (
            os.environ.get("COMPONENTS_REPO_URL")
            or os.environ.get("PI_SELFHOSTING_COMPONENTS_REPO")
            or "HenkVanHoek/njord-deploy-components"
        ).strip()
        branch = (
            os.environ.get("COMPONENTS_REPO_BRANCH")
            or os.environ.get("PI_SELFHOSTING_COMPONENTS_BRANCH")
            or "main"
        ).strip()
        token = os.environ.get("COMPONENTS_REPO_TOKEN", "").strip()

        is_disabled = repo.lower() in ("none", "local", "offline", "")
        return {
            "url": repo,
            "branch": branch,
            "token": token,
            "is_enabled": not is_disabled,
        }

    @classmethod
    def is_remote_sync_enabled(cls) -> bool:
        """Returns True if remote components sync is active."""
        config = cls.get_repo_config()
        return bool(config.get("is_enabled", True))

    @classmethod
    def get_repo_urls(cls) -> tuple[str, str]:
        """Returns (ssh_url, https_url) for the configured repository."""
        config = cls.get_repo_config()
        repo = str(config.get("url", "HenkVanHoek/njord-deploy-components"))

        if repo.startswith("git@") or repo.startswith("ssh://"):
            return repo, repo
        if repo.startswith("https://") or repo.startswith("http://"):
            https_url = repo if repo.endswith(".git") else f"{repo}.git"
            return repo, https_url

        # Default GitHub slug owner/repo
        ssh_url = f"git@github.com:{repo}.git"
        https_url = f"https://github.com/{repo}.git"
        return ssh_url, https_url

    @classmethod
    def validate_remote_repo(
        cls,
        url: str,
        branch: str = "main",
        token: Optional[str] = None,
        timeout: int = 4,
    ) -> tuple[bool, str]:
        """
        Validates whether a remote repository or archive URL is reachable.
        """
        cleaned = url.strip()
        if cleaned.lower() in ("none", "local", "offline", ""):
            return True, "Local-only mode configured (remote sync disabled)"

        # Construct candidate download URL
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            if cleaned.endswith(".zip"):
                download_url = cleaned
            elif "gitlab." in cleaned:
                base = cleaned.rstrip(".git")
                download_url = f"{base}/-/archive/{branch}/components-{branch}.zip"
            else:
                download_url = (
                    f"{cleaned.rstrip('.git')}/archive/refs/heads/{branch}.zip"
                )
        else:
            download_url = (
                f"https://github.com/{cleaned}/archive/refs/heads/{branch}.zip"
            )

        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            res = requests.head(
                download_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
            if res.status_code in (200, 302, 301):
                return True, f"Repository archive reachable at {download_url}"
            # Some servers block HEAD, try GET with range or timeout
            res_get = requests.get(
                download_url,
                headers={**headers, "Range": "bytes=0-10"},
                timeout=timeout,
                stream=True,
            )
            if res_get.status_code in (200, 206, 302, 301):
                return True, f"Repository archive reachable at {download_url}"
            return (
                False,
                f"Repository check returned status {res_get.status_code} "
                f"for {download_url}",
            )
        except Exception as e:
            return False, f"Connection failed to {download_url}: {str(e)}"

    def fetch_from_remote(self, timeout: int = 3) -> bool:
        """
        Downloads the latest ZIP from repository and extracts it to the cache directory.
        Returns True if successful, False if network is offline or request failed.
        """
        config = self.get_repo_config()
        if not config.get("is_enabled"):
            logger.info("Remote sync is disabled by configuration (local-only mode).")
            self.is_offline = False
            return False

        repo = str(config.get("url"))
        branch = str(config.get("branch"))
        token = str(config.get("token", ""))

        if repo.startswith("http://") or repo.startswith("https://"):
            if repo.endswith(".zip"):
                url = repo
            elif "gitlab." in repo:
                base = repo.rstrip(".git")
                url = f"{base}/-/archive/{branch}/components-{branch}.zip"
            else:
                url = f"{repo.rstrip('.git')}/archive/refs/heads/{branch}.zip"
        else:
            url = f"https://github.com/{repo}/archive/refs/heads/{branch}.zip"

        # Check if git cache exists and can be updated via git pull
        if self.git_repo_dir.exists() and (self.git_repo_dir / ".git").exists():
            import subprocess  # nosec B404

            # noinspection PyBroadException
            try:
                res = subprocess.run(  # nosec B603 B607
                    ["git", "pull"],
                    cwd=str(self.git_repo_dir),
                    capture_output=True,
                    text=True,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    timeout=10,
                )
                if res.returncode == 0:
                    self._update_cache_from_git_repo()
                    self.is_offline = False
                    logger.info("Successfully fetched components via git pull")
                    return True
            except Exception as e:
                logger.info(
                    f"Git pull in cache skipped/failed, falling back to ZIP: {e}"
                )

        headers = {"Authorization": f"token {token}"} if token else None

        try:
            logger.info(f"Fetching remote components from {url} (timeout={timeout}s)")
            if headers:
                response = requests.get(url, headers=headers, timeout=timeout)
            else:
                response = requests.get(url, timeout=timeout)
            if response.status_code != 200:
                logger.warning(
                    f"Failed to download repository ZIP from {url}. "
                    f"Status code: {response.status_code}"
                )
                self.is_offline = False
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

                repo_root = next(iter(subdirs), None)
                if not repo_root:
                    return False

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

            self.is_offline = False
            logger.info("Successfully fetched and cached remote components")
            return True
        except (requests.exceptions.RequestException, OSError) as e:
            self.is_offline = True
            logger.info(f"Remote fetch skipped/failed (offline or timeout): {e}")
            return False
        except Exception as e:
            self.is_offline = True
            logger.error(f"Error fetching remote components: {e}", exc_info=True)
            return False

    def _load_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        # noinspection PyBroadException
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def get_local_component_meta(self, component_id: str) -> dict:
        """Retrieves local component metadata from components_metadata.json."""
        return self._get_local_component_meta(component_id)

    def get_remote_component_meta(self, component_id: str) -> dict:
        """Retrieves remote component metadata from cache."""
        return self._get_remote_component_meta(component_id)

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
            # noinspection PyBroadException
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
        component_timestamps = {}
        remote_updates_available = 0

        for comp_id in all_comps:
            comp_status = self.compare_component(comp_id)
            status_dict[comp_id] = comp_status
            if comp_status in ("modified", "remote_only"):
                remote_updates_available += 1

            local_meta = local_data.get("components", {}).get(comp_id, {})
            component_timestamps[comp_id] = {
                "last_updated": local_meta.get("last_updated"),
                "last_tested": local_meta.get("last_tested"),
                "test_status": local_meta.get("test_status", "untested"),
            }

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
            "is_offline": self.is_offline,
            "components": status_dict,
            "component_timestamps": component_timestamps,
            "remote_updates_available": remote_updates_available,
            "global_metadata_out_of_sync": global_out_of_sync,
        }

    def mark_component_tested(
        self, component_id: str, test_status: str = "stable"
    ) -> bool:
        """Updates last_tested timestamp and test_status for a component."""
        data = self._load_json(self.local_metadata_path)
        comp = data.get("components", {}).get(component_id)
        if not comp:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        comp["last_tested"] = now_iso
        comp["test_status"] = test_status

        try:
            with open(self.local_metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to update last_tested for {component_id}: {e}")
            return False

    def update_component_timestamp(self, component_id: str) -> bool:
        """Updates last_updated timestamp for a component."""
        data = self._load_json(self.local_metadata_path)
        comp = data.get("components", {}).get(component_id)
        if not comp:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        comp["last_updated"] = now_iso

        try:
            with open(self.local_metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to update last_updated for {component_id}: {e}")
            return False

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

    def check_write_access_details(self) -> tuple[bool, str]:
        """Verifies if the local environment has write access to the components'
        repository and returns (has_write_access, details_message).
        """
        import subprocess  # nosec B404

        # noinspection PyBroadException
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

        last_err = ""
        # Try SSH push dry run
        ssh_url = "git@github.com:HenkVanHoek/njord-deploy-components.git"
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
                return True, "Write permissions verified via SSH"
            last_err = (
                res.stderr.strip() or f"SSH check exited with code {res.returncode}"
            )
        except Exception as e:
            logger.error(f"SSH write access check failed: {e}")
            last_err = str(e)

        # Try HTTPS push dry run
        ssh_url, https_url = self.get_repo_urls()
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
                return True, "Write permissions verified via HTTPS"
            last_err = (
                res.stderr.strip() or f"HTTPS check exited with code {res.returncode}"
            )
        except Exception as e:
            logger.error(f"HTTPS write access check failed: {e}")
            last_err = str(e)

        return False, last_err or "No write permissions for repository"

    def check_write_access(self) -> bool:
        """Verifies if the local environment has write access to the components'
        repository.
        """
        has_write, _ = self.check_write_access_details()
        return has_write

    def _prepare_git_repo(self) -> str:
        """Clones or updates the local git cache for components repo."""
        self.git_repo_dir.parent.mkdir(parents=True, exist_ok=True)
        ssh_url, https_url = self.get_repo_urls()

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

    def _resolve_component_dir(self, component_id: str) -> Path | None:
        """Finds existing template directory for component_id.

        Tries alternate hyphen/underscore forms if needed.
        """
        possible_names = [
            component_id,
            (
                component_id.replace("home", "-home")
                if "home" in component_id and "-home" not in component_id
                else component_id
            ),
            component_id.replace("-", ""),
            component_id.replace("_", "-"),
            component_id.replace("-", "_"),
        ]
        for name in possible_names:
            p = self.local_templates_path / name
            if p.exists() and (p / "docker-compose.template.yml").exists():
                return p
        return None

    def validate_metadata_header(self, component_id: str) -> bool:
        """Checks if the component template has the four metadata header comments."""
        filename = "docker-compose.template.yml"
        comp_dir = self._resolve_component_dir(component_id)
        if not comp_dir:
            return False
        filepath = comp_dir / filename

        # noinspection PyBroadException
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
        src_dir = self._resolve_component_dir(component_id)
        if not src_dir:
            src_dir = self.local_templates_path / component_id
        if not src_dir.exists():
            raise FileNotFoundError(f"Local template dir {src_dir} does not exist.")

        target_id = src_dir.name
        dest_dir = self.git_repo_dir / "component_templates" / target_id

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.copytree(src_dir, dest_dir)

        # 3. Update components_metadata.json in the git repo
        local_data = self._load_json(self.local_metadata_path)
        remote_metadata_path = self.git_repo_dir / "components_metadata.json"
        remote_data = self._load_json(remote_metadata_path)

        if "components" not in remote_data:
            remote_data["components"] = {}

        # Look up metadata using component_id or resolved target_id
        meta_id = (
            component_id
            if component_id in local_data.get("components", {})
            else target_id
        )
        if meta_id in local_data.get("components", {}):
            remote_data["components"][target_id] = local_data["components"][meta_id]
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

        self._update_cache_for_component(component_id)
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
            self._update_cache_all()
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

        self._update_cache_all()
        return True

    def _update_cache_for_component(self, component_id: str) -> None:
        """Updates the remote cache for a single component after successful push."""
        # Update metadata in cache
        if self.cache_metadata_path.exists():
            local_data = self._load_json(self.local_metadata_path)
            cache_data = self._load_json(self.cache_metadata_path)
            if "components" not in cache_data:
                cache_data["components"] = {}
            if component_id in local_data.get("components", {}):
                cache_data["components"][component_id] = local_data["components"][
                    component_id
                ]
                # noinspection PyBroadException
                try:
                    with open(self.cache_metadata_path, "w", encoding="utf-8") as f:
                        json.dump(cache_data, f, indent=4)
                except Exception as e:
                    logger.warning(
                        f"Failed to update cache metadata for {component_id}: {e}"
                    )

        # Update templates in cache
        src_dir = self._resolve_component_dir(component_id)
        if not src_dir:
            src_dir = self.local_templates_path / component_id
        if src_dir.exists():
            dest_dir = self.cache_templates_path / src_dir.name
            # noinspection PyBroadException
            try:
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                dest_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src_dir, dest_dir)
            except Exception as e:
                logger.warning(
                    f"Failed to update cache templates for {component_id}: {e}"
                )

    def _update_cache_all(self) -> None:
        """Updates the entire remote cache after successful bulk push."""
        # noinspection PyBroadException
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if self.local_metadata_path.exists():
                shutil.copy2(self.local_metadata_path, self.cache_metadata_path)
            if self.local_templates_path.exists():
                if self.cache_templates_path.exists():
                    shutil.rmtree(self.cache_templates_path)
                shutil.copytree(self.local_templates_path, self.cache_templates_path)
        except Exception as e:
            logger.warning(f"Failed to update full cache after bulk upload: {e}")

    def _update_cache_from_git_repo(self) -> None:
        """Updates the remote cache from the local git repository clone."""
        # noinspection PyBroadException
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            git_meta = self.git_repo_dir / "components_metadata.json"
            git_templates = self.git_repo_dir / "component_templates"
            if git_meta.exists():
                shutil.copy2(git_meta, self.cache_metadata_path)
            if git_templates.exists():
                if self.cache_templates_path.exists():
                    shutil.rmtree(self.cache_templates_path)
                shutil.copytree(git_templates, self.cache_templates_path)
        except Exception as e:
            logger.warning(f"Failed to update cache from git clone: {e}")
