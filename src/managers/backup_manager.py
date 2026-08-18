"""NjordDeploy Backup & Restore Manager.

Provides comprehensive volume discovery, data archiving, integrity validation,
and restoration specifically for services managed by NjordDeploy.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "This backup tool exclusively detects, archives, and restores services, "
    "configurations, and persistent volumes managed by NjordDeploy under "
    "the active stack directory. External host directories and unmanaged "
    "containers are not affected."
)


def _format_size(size_bytes: int) -> str:
    """Formats bytes into a human-readable string (KB, MB, GB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    val = float(size_bytes)
    while val >= 1024.0 and unit_index < len(units) - 1:
        val /= 1024.0
        unit_index += 1
    return f"{val:.1f} {units[unit_index]}"


class BackupManager:
    """Manages volume inspection, tarball archiving, and state restoration

    for NjordDeploy-managed services across configurable stack directories.
    """

    def __init__(
        self,
        component_manager: Any = None,
        project_config_dir: str = "/opt/njorddeploy",
    ) -> None:
        """Initialize the BackupManager."""
        self.component_manager = component_manager
        self.project_config_dir = project_config_dir

    def resolve_project_dir(
        self, ssh_manager: Any, custom_dir: Optional[str] = None
    ) -> str:
        """Resolves the remote project directory containing compose files,

        expanding tildes and checking candidate paths.
        """
        null_log = lambda msg: None  # noqa: E731
        target_dir = (custom_dir or self.project_config_dir).strip()

        # If ssh_manager is not connected or mock has no execute_command
        if not hasattr(ssh_manager, "execute_command"):
            return target_dir

        # Remote shell script to expand candidate directories and detect compose files
        cmd = (
            f'for d in "{target_dir}" "$HOME/docker" '
            f'/opt/njorddeploy "$HOME/njorddeploy"; do '
            f'  expanded=$(eval echo "$d" 2>/dev/null); '
            f'  if [ -n "$expanded" ]; then '
            f'    if [ -f "$expanded/docker-compose.yml" ] || '
            f'       [ -f "$expanded/docker-compose.yaml" ] || '
            f'       [ -f "$expanded/compose.yml" ] || '
            f'       [ -f "$expanded/compose.yaml" ]; then '
            f'      echo "$expanded"; '
            f"      break; "
            f"    fi; "
            f"  fi; "
            f"done"
        )
        try:
            res = ssh_manager.execute_command(cmd, null_log, check_exit_code=False)
            stdout = (
                res[1] if isinstance(res, tuple) and len(res) >= 2 else str(res or "")
            )
        except Exception:
            stdout = ""

        lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
        if lines:
            first_resolved, *_ = lines
            if first_resolved.startswith("/"):
                return first_resolved

        return target_dir

    def discover_compose_files(
        self,
        ssh_manager: Any,
        search_roots: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Scans target host filesystem for existing docker-compose / compose files."""
        null_log = lambda msg: None  # noqa: E731
        if not hasattr(ssh_manager, "execute_command"):
            return []

        search_dirs = search_roots or [
            "/opt",
            "/home",
            "$HOME",
            "/srv",
            "/etc/docker",
        ]
        dirs_str = " ".join(f'"{d}"' for d in search_dirs)
        cmd = (
            f"for root in {dirs_str}; do "
            f'  exp=$(eval echo "$root" 2>/dev/null); '
            f'  if [ -n "$exp" ] && [ -d "$exp" ]; then '
            f'    find "$exp" -maxdepth 4 -type f \\( '
            f"      -name 'docker-compose.yml' -o "
            f"      -name 'docker-compose.yaml' -o "
            f"      -name 'compose.yml' -o "
            f"      -name 'compose.yaml' "
            f"    \\) 2>/dev/null; "
            f"  fi; "
            f"done | sort -u | head -n 25"
        )
        try:
            res = ssh_manager.execute_command(cmd, null_log, check_exit_code=False)
            stdout = (
                res[1] if isinstance(res, tuple) and len(res) >= 2 else str(res or "")
            )
        except Exception:
            stdout = ""

        results: List[Dict[str, str]] = []
        for line in stdout.splitlines():
            filepath = line.strip()
            if not filepath:
                continue
            directory = os.path.dirname(filepath)
            filename = os.path.basename(filepath)
            results.append(
                {
                    "directory": directory,
                    "compose_file": filepath,
                    "filename": filename,
                }
            )

        def sort_key(item: Dict[str, str]) -> int:
            d = item.get("directory", "")
            if "/opt/njorddeploy" in d:
                return 0
            if "/docker" in d:
                return 1
            return 2

        results.sort(key=sort_key)
        return results

    def parse_compose_volumes(
        self, compose_yaml_content: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Parses service volume mount definitions from a Docker Compose YAML string.

        Returns a dictionary mapping service_id -> list of volume dicts.
        """
        if not compose_yaml_content or not compose_yaml_content.strip():
            return {}

        try:
            data = yaml.safe_load(compose_yaml_content)
        except Exception as e:
            logger.error(f"Failed to parse compose YAML: {e}")
            return {}

        if not isinstance(data, dict):
            return {}

        services = data.get("services", {})
        if not isinstance(services, dict):
            return {}

        result: Dict[str, List[Dict[str, Any]]] = {}

        for service_name, service_data in services.items():
            if not isinstance(service_data, dict):
                continue

            volumes = service_data.get("volumes", [])
            if not isinstance(volumes, list):
                continue

            service_volumes: List[Dict[str, Any]] = []
            for vol_entry in volumes:
                if isinstance(vol_entry, str):
                    clean_entry = vol_entry.strip().strip("'\"")
                    # Handle host_path:container_path[:mode]
                    parts = clean_entry.split(":")
                    if len(parts) >= 2:
                        host_target, container_target, *rest = parts
                        host_path = host_target.strip()
                        container_path = container_target.strip()
                        mode = rest[0].strip() if rest else "rw"
                        is_bind = host_path.startswith("/") or host_path.startswith("~")
                        service_volumes.append(
                            {
                                "raw": clean_entry,
                                "type": "bind" if is_bind else "volume",
                                "host_path": host_path,
                                "container_path": container_path,
                                "mode": mode,
                            }
                        )
                elif isinstance(vol_entry, dict):
                    vol_type = vol_entry.get("type", "bind")
                    source = vol_entry.get("source", "")
                    target = vol_entry.get("target", "")
                    if source and target:
                        service_volumes.append(
                            {
                                "raw": f"{source}:{target}",
                                "type": vol_type,
                                "host_path": str(source),
                                "container_path": str(target),
                                "mode": "ro" if vol_entry.get("read_only") else "rw",
                            }
                        )

            result[service_name] = service_volumes

        return result

    def inspect_target(
        self,
        ssh_manager: Any,
        project_config_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects remote NjordDeploy installation to discover managed services,

        their volumes, and calculated storage footprints.
        """
        null_log = lambda msg: None  # noqa: E731
        active_dir = self.resolve_project_dir(ssh_manager, project_config_dir)

        # Check for compose file under active_dir
        cmd_check = (
            f'for f in "{active_dir}/docker-compose.yml" '
            f'"{active_dir}/docker-compose.yaml" '
            f'"{active_dir}/compose.yml" '
            f'"{active_dir}/compose.yaml"; do '
            f'  if [ -f "$f" ]; then '
            f"    echo '___COMPOSE_FOUND___'; "
            f'    cat "$f"; '
            f"    echo '___COMPOSE_END___'; "
            f"    break; "
            f"  fi; "
            f"done"
        )
        exit_code, stdout = ssh_manager.execute_command(
            cmd_check, null_log, check_exit_code=False
        )

        if exit_code != 0 or "___COMPOSE_FOUND___" not in stdout:
            return {
                "status": "error",
                "message": (
                    f"No docker-compose.yml or compose.yaml found at '{active_dir}'."
                ),
                "managed_scope": active_dir,
                "disclaimer": DISCLAIMER_TEXT,
                "components": [],
                "total_managed_size_bytes": 0,
                "total_managed_size_human": "0 B",
            }

        # Extract compose YAML content cleanly
        after_marker = stdout.split("___COMPOSE_FOUND___", 1)[1]
        if "___COMPOSE_END___" in after_marker:
            compose_content = after_marker.split("___COMPOSE_END___", 1)[0]
        else:
            compose_content = after_marker
        service_volumes = self.parse_compose_volumes(compose_content)
        components_list: List[Dict[str, Any]] = []
        total_bytes = 0

        # Discover sizes for each service volume
        for service_id, volumes in service_volumes.items():
            service_bytes = 0
            enriched_volumes: List[Dict[str, Any]] = []

            for vol in volumes:
                host_path = vol.get("host_path", "")
                is_bind = vol.get("type") == "bind"
                size_bytes = 0

                if is_bind and host_path:
                    # Query disk usage in bytes on remote host
                    cmd_du = (
                        f'expanded_p=$(eval echo "{host_path}" 2>/dev/null); '
                        f'if [ -e "$expanded_p" ]; then '
                        f'du -sb "$expanded_p" 2>/dev/null || '
                        f'du -sk "$expanded_p" 2>/dev/null | '
                        f"awk '{{print $1 * 1024}}'; "
                        f"else echo '0'; fi"
                    )
                    _, du_out = ssh_manager.execute_command(
                        cmd_du, null_log, check_exit_code=False
                    )
                    for line in du_out.splitlines():
                        line_str = line.strip()
                        first_col = line_str.split()[0] if line_str.split() else ""
                        if first_col.isdigit():
                            size_bytes = int(first_col)
                            break

                vol_dict = dict(vol)
                vol_dict["size_bytes"] = size_bytes
                vol_dict["size_human"] = _format_size(size_bytes)
                service_bytes += size_bytes
                enriched_volumes.append(vol_dict)

            # Heuristic: mark large volumes or media/recording/upload dirs
            is_heavy = service_bytes > 500 * 1024 * 1024 or any(
                k in service_id.lower()
                for k in ["frigate", "nextcloud", "immich", "jellyfin", "plex"]
            )

            components_list.append(
                {
                    "id": service_id,
                    "name": service_id.replace("-", " ").title(),
                    "container_name": f"njorddeploy-{service_id}",
                    "volumes": enriched_volumes,
                    "total_size_bytes": service_bytes,
                    "total_size_human": _format_size(service_bytes),
                    "is_heavy": is_heavy,
                }
            )
            total_bytes += service_bytes

        return {
            "status": "success",
            "managed_scope": active_dir,
            "disclaimer": DISCLAIMER_TEXT,
            "components": components_list,
            "total_managed_size_bytes": total_bytes,
            "total_managed_size_human": _format_size(total_bytes),
        }

    def create_backup(
        self,
        ssh_manager: Any,
        selected_components: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        pause_containers: bool = False,
        project_config_dir: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Creates a timestamped compressed backup tarball of NjordDeploy services."""
        log = log_callback or (lambda msg: None)
        active_dir = self.resolve_project_dir(ssh_manager, project_config_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"njorddeploy_backup_{timestamp}.tar.gz"
        backup_dir = f"{active_dir}/backups"
        backup_path = f"{backup_dir}/{backup_filename}"
        staging_dir = f"{backup_dir}/staging_{timestamp}"

        exclude_paths = exclude_paths or []
        log(f"Initiating NjordDeploy Backup: {backup_filename}\n")
        log(f"Scope / Stack Directory: {active_dir}\n")

        # 1. Inspect target to resolve exact volume paths
        inspection = self.inspect_target(ssh_manager, project_config_dir=active_dir)
        if inspection.get("status") != "success":
            msg = inspection.get("message", "Target inspection failed.")
            log(f"ERROR: {msg}\n")
            return {"status": "error", "message": msg}

        all_components = inspection.get("components", [])
        if selected_components is not None:
            active_components = [
                c for c in all_components if c.get("id") in selected_components
            ]
        else:
            active_components = all_components

        if not active_components and all_components:
            log("No valid components selected for backup.\n")
            return {"status": "error", "message": "No components selected."}

        included_service_ids = [c["id"] for c in active_components]
        log(f"Backing up services: {', '.join(included_service_ids)}\n")

        # 2. Gather host paths to archive
        paths_to_archive: List[str] = [
            f"{active_dir}/docker-compose.yml",
            f"{active_dir}/docker-compose.yaml",
            f"{active_dir}/compose.yml",
            f"{active_dir}/compose.yaml",
            f"{active_dir}/.env",
        ]

        for comp in active_components:
            for vol in comp.get("volumes", []):
                h_path = vol.get("host_path", "")
                if vol.get("type") == "bind" and h_path and h_path not in exclude_paths:
                    if h_path not in paths_to_archive:
                        paths_to_archive.append(h_path)

        # 3. Create staging and metadata manifest
        manifest_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "scope": active_dir,
            "disclaimer": DISCLAIMER_TEXT,
            "components": included_service_ids,
            "archived_paths": paths_to_archive,
            "excluded_paths": exclude_paths,
        }

        manifest_json_str = json.dumps(manifest_data, indent=2)

        # 4. Prepare remote backup directories
        prep_cmd = (
            f'mkdir -p "{backup_dir}" && '
            f'mkdir -p "{staging_dir}" && '
            f"cat << 'EOF' > \"{staging_dir}/manifest.json\"\n"
            f"{manifest_json_str}\n"
            f"EOF\n"
        )
        ssh_manager.execute_command(prep_cmd, log)

        # 5. Optionally pause containers for transactional consistency
        if pause_containers and included_service_ids:
            log("Pausing active containers for transactional consistency...\n")
            pause_cmd = (
                f'cd "{active_dir}" && '
                f"docker compose pause {' '.join(included_service_ids)} "
                f"2>/dev/null || true"
            )
            ssh_manager.execute_command(pause_cmd, log, check_exit_code=False)

        # 6. Archive configuration and volume directories into tarball
        existing_check = []
        for p in paths_to_archive:
            existing_check.append(
                f'ep=$(eval echo "{p}" 2>/dev/null); '
                f'[ -e "$ep" ] && printf \'%s\n\' "$ep"'
            )
        gather_existing_cmd = " ; ".join(existing_check)

        log("Building compressed backup tarball...\n")
        tar_cmd = (
            f"valid_paths=$({gather_existing_cmd}) ; "
            f'if [ -n "$valid_paths" ]; then '
            f'tar -czf "{backup_path}" '
            f'-C "{staging_dir}" manifest.json '
            f"$valid_paths 2>/dev/null || "
            f'tar -czf "{backup_path}" -C "{staging_dir}" manifest.json ; '
            f"else "
            f'tar -czf "{backup_path}" -C "{staging_dir}" manifest.json ; '
            f"fi"
        )

        tar_code, _ = ssh_manager.execute_command(tar_cmd, log, check_exit_code=False)

        # 7. Unpause containers
        if pause_containers and included_service_ids:
            log("Resuming container operations...\n")
            unpause_cmd = (
                f'cd "{active_dir}" && '
                f"docker compose unpause {' '.join(included_service_ids)} "
                f"2>/dev/null || true"
            )
            ssh_manager.execute_command(unpause_cmd, log, check_exit_code=False)

        # 8. Clean up staging
        cleanup_cmd = f'rm -rf "{staging_dir}"'
        ssh_manager.execute_command(cleanup_cmd, log, check_exit_code=False)

        if tar_code != 0:
            log("ERROR: Tar archiving failed.\n")
            return {"status": "error", "message": "Failed to create archive tarball."}

        # 9. Compute sha256 checksum and size of the created backup
        hash_cmd = (
            f"sha256sum \"{backup_path}\" 2>/dev/null | awk '{{print $1}}' ; "
            f"stat -c %s \"{backup_path}\" 2>/dev/null || echo '0'"
        )
        _, hash_out = ssh_manager.execute_command(hash_cmd, log, check_exit_code=False)
        lines = [ln.strip() for ln in hash_out.splitlines() if ln.strip()]
        sha256_hash = ""
        size_bytes = 0
        if len(lines) >= 2:
            first_item, second_item, *_ = lines
            sha256_hash = first_item
            if second_item.isdigit():
                size_bytes = int(second_item)
        elif len(lines) == 1:
            first_item, *_ = lines
            sha256_hash = first_item

        log(f"SUCCESS: Backup created successfully ({_format_size(size_bytes)}).\n")
        log(f"SHA-256: {sha256_hash}\n")

        return {
            "status": "success",
            "filename": backup_filename,
            "remote_path": backup_path,
            "size_bytes": size_bytes,
            "size_human": _format_size(size_bytes),
            "sha256": sha256_hash,
            "created_at": datetime.now().isoformat(),
            "components": included_service_ids,
            "managed_scope": active_dir,
            "disclaimer": DISCLAIMER_TEXT,
        }

    def list_backups(
        self,
        ssh_manager: Any,
        project_config_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists available NjordDeploy backup archives on the remote host."""
        null_log = lambda msg: None  # noqa: E731
        active_dir = self.resolve_project_dir(ssh_manager, project_config_dir)
        backup_dir = f"{active_dir}/backups"
        list_cmd = (
            f'if [ -d "{backup_dir}" ]; then '
            f'for f in "{backup_dir}"/njorddeploy_backup_*.tar.gz; do '
            f'  if [ -f "$f" ]; then '
            f"    stat -c '%n|%s|%Y' \"$f\" 2>/dev/null; "
            f"  fi; "
            f"done; "
            f"fi"
        )
        exit_code, stdout = ssh_manager.execute_command(
            list_cmd, null_log, check_exit_code=False
        )

        results: List[Dict[str, Any]] = []
        if exit_code != 0 or not stdout.strip():
            return results

        for line in stdout.splitlines():
            line_str = line.strip()
            if not line_str or "|" not in line_str:
                continue

            parts = line_str.split("|")
            if len(parts) >= 3:
                f_path, size_str, mtime_str, *_ = parts
                f_name = os.path.basename(f_path)
                size_b = int(size_str) if size_str.isdigit() else 0
                mtime_int = int(mtime_str) if mtime_str.isdigit() else 0
                dt_str = (
                    datetime.fromtimestamp(mtime_int).strftime("%Y-%m-%d %H:%M:%S")
                    if mtime_int > 0
                    else "Unknown"
                )

                results.append(
                    {
                        "filename": f_name,
                        "remote_path": f_path,
                        "size_bytes": size_b,
                        "size_human": _format_size(size_b),
                        "created_at": dt_str,
                        "timestamp": mtime_int,
                        "stack_dir": active_dir,
                    }
                )

        # Sort newest first
        results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return results

    def restore_backup(
        self,
        ssh_manager: Any,
        backup_filename: str,
        selected_components: Optional[List[str]] = None,
        restart_after: bool = True,
        project_config_dir: Optional[str] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Restores services and volumes from a NjordDeploy backup tarball."""
        log = log_callback or (lambda msg: None)
        active_dir = self.resolve_project_dir(ssh_manager, project_config_dir)

        # Sanitize filename
        clean_filename = os.path.basename(backup_filename.strip())
        if not re.match(r"^njorddeploy_backup_[0-9_]+\.tar\.gz$", clean_filename):
            msg = f"Invalid backup filename: {clean_filename}"
            log(f"ERROR: {msg}\n")
            return {"status": "error", "message": msg}

        backup_path = f"{active_dir}/backups/{clean_filename}"
        log(f"Initiating Restore from: {clean_filename}\n")
        log(f"Scope / Stack Directory: {active_dir}\n")

        # 1. Verify archive existence on target
        check_cmd = (
            f'if [ -f "{backup_path}" ]; then '
            f'tar -tzf "{backup_path}" manifest.json >/dev/null 2>&1 && '
            f"echo 'VALID'; "
            f"else echo 'MISSING'; fi"
        )
        _, check_out = ssh_manager.execute_command(
            check_cmd, log, check_exit_code=False
        )

        if "VALID" not in check_out:
            msg = f"Backup archive {clean_filename} not found at {backup_path}."
            log(f"ERROR: {msg}\n")
            return {"status": "error", "message": msg}

        # 2. Extract manifest to inspect metadata
        manifest_cmd = (
            f"tar -xzf \"{backup_path}\" manifest.json -O 2>/dev/null || echo '{{}}'"
        )
        _, manifest_out = ssh_manager.execute_command(
            manifest_cmd, log, check_exit_code=False
        )
        try:
            manifest_data = json.loads(manifest_out)
        except Exception:
            manifest_data = {}

        archived_components = manifest_data.get("components", [])

        # 3. Stop running containers before extracting volume state
        log("Stopping current container stack...\n")
        stop_cmd = f'cd "{active_dir}" && docker compose stop 2>/dev/null || true'
        ssh_manager.execute_command(stop_cmd, log, check_exit_code=False)

        # 4. Extract archive to root filesystem
        log("Extracting configuration and volume data from backup archive...\n")
        extract_cmd = f'tar -xzf "{backup_path}" -C /'
        extract_code, _ = ssh_manager.execute_command(
            extract_cmd, log, check_exit_code=False
        )

        if extract_code != 0:
            log("ERROR: Failed to extract backup tarball.\n")
            return {"status": "error", "message": "Tar extraction failed."}

        # 5. Fix permissions on restored mount directories
        log("Applying directory permissions to restored volumes...\n")
        fix_perms_cmd = (
            f"for f in '{active_dir}/docker-compose.yml' "
            f"'{active_dir}/compose.yml'; do "
            f'  if [ -f "$f" ]; then '
            f"    grep -E '^\\s*-\\s+/[^:]+:' \"$f\" | "
            f"    sed -E 's/^\\s*-\\s+([^:]+):.*/\\1/' | while read -r host_path; do "
            f'      clean_p=$(echo "$host_path" | tr -d \'"\' | tr -d "\'"); '
            f'      if [ -n "$clean_p" ] && [ -d "$clean_p" ]; then '
            f'        chmod -R 777 "$clean_p" 2>/dev/null || true; '
            f"      fi; "
            f"    done; "
            f"  fi; "
            f"done"
        )
        ssh_manager.execute_command(fix_perms_cmd, log, check_exit_code=False)

        # 6. Restart container stack if requested
        if restart_after:
            log("Restarting container stack with restored data...\n")
            up_cmd = f'cd "{active_dir}" && docker compose up -d 2>&1'
            ssh_manager.execute_command(up_cmd, log, check_exit_code=False)

        log("SUCCESS: Restore operation completed successfully.\n")
        return {
            "status": "success",
            "restored_archive": clean_filename,
            "restored_components": (selected_components or archived_components),
            "restarted": restart_after,
            "managed_scope": active_dir,
            "disclaimer": DISCLAIMER_TEXT,
        }

    def download_backup_sftp(
        self,
        ssh_manager: Any,
        remote_filename: str,
        local_destination_dir: Path,
        project_config_dir: Optional[str] = None,
    ) -> Tuple[bool, str, Path]:
        """Downloads a remote backup archive file to the local machine via SFTP."""
        clean_filename = os.path.basename(remote_filename.strip())
        active_dir = self.resolve_project_dir(ssh_manager, project_config_dir)
        remote_path = f"{active_dir}/backups/{clean_filename}"
        local_destination_dir.mkdir(parents=True, exist_ok=True)
        local_file = local_destination_dir / clean_filename

        if not ssh_manager.client:
            return False, "SSH client is not connected.", local_file

        try:
            sftp = ssh_manager.client.open_sftp()
            sftp.get(remote_path, str(local_file))
            sftp.close()
            return True, "Download successful.", local_file
        except Exception as e:
            return False, str(e), local_file
