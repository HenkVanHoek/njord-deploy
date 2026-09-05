# Proxmox Automated Package Testing Report

**Run Timestamp:** 2026-09-05 16:25:54
**Total Packages Tested:** 25 | **Passed:** 23 | **Failed:** 2

## Packages Summary Table

| Package ID | Package Name | Target | Engine | VM ID | IP Address | Deployment | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy-filebrowser-stack` | Reverse Proxy & Remote Workspace | LXC | DOCKER | 109 | 10.99.0.199 | success | **✅ PASS** |
| `dns-shield-stack` | DNS & Ad-Blocking Privacy Shield | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `monitoring-stack` | Monitoring Stack | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `digital-archive` | Digital Archive & Document Compliance | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `observability-analytics` | Observability & Privacy Analytics | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | LXC | DOCKER | 108 | 10.99.0.199 | failed | **❌ FAIL** |
| `agile-ops` | Agile Operations & Secure Chat | LXC | DOCKER | 104 | 10.99.0.199 | success | **✅ PASS** |
| `smarthome-stack` | Sovereign Smart Home Hub | LXC | DOCKER | 106 | 192.168.178.36 | success | **✅ PASS** |
| `nextcloud-stack` | Nextcloud Stack | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `modern-workplace` | The Modern Sovereign Workplace | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `media-stack` | Media Streaming & Servarr Suite | LXC | DOCKER | 108 | 10.99.0.199 | success | **✅ PASS** |
| `agile-ops` | Agile Operations & Secure Chat | VM | DOCKER | 104 | 10.99.0.199 | success | **✅ PASS** |
| `caddy-filebrowser-stack` | Reverse Proxy & Remote Workspace | VM | DOCKER | 104 | 192.168.178.147 | success | **✅ PASS** |
| `digital-archive` | Digital Archive & Document Compliance | VM | DOCKER | 104 | 192.168.178.143 | success | **❌ FAIL** |
| `dns-shield-stack` | DNS & Ad-Blocking Privacy Shield | VM | DOCKER | 104 | 192.168.178.22 | success | **✅ PASS** |
| `media-stack` | Media Streaming & Servarr Suite | VM | DOCKER | 104 | 192.168.178.128 | success | **✅ PASS** |
| `modern-workplace` | The Modern Sovereign Workplace | VM | DOCKER | 104 | 192.168.178.175 | success | **✅ PASS** |
| `monitoring-stack` | Monitoring Stack | VM | DOCKER | 104 | 192.168.178.179 | success | **✅ PASS** |
| `nextcloud-stack` | Nextcloud Stack | VM | DOCKER | 104 | 192.168.178.168 | success | **✅ PASS** |
| `observability-analytics` | Observability & Privacy Analytics | VM | DOCKER | 104 | 192.168.178.184 | success | **✅ PASS** |
| `open-webui-ollama` | Open WebUI & Ollama AI Studio | VM | DOCKER | 104 | 192.168.178.178 | success | **✅ PASS** |
| `smarthome-stack` | Sovereign Smart Home Hub | VM | DOCKER | 104 | 192.168.178.172 | success | **✅ PASS** |
| `agile-ops` | Agile Operations & Secure Chat | LXC | PODMAN | 104 | 10.99.0.199 | success | **✅ PASS** |
| `caddy-filebrowser-stack` | Reverse Proxy & Remote Workspace | LXC | PODMAN | 104 | 10.99.0.199 | success | **✅ PASS** |
| `agile-ops` | Agile Operations & Secure Chat | VM | PODMAN | 104 | 10.99.0.199 | success | **✅ PASS** |

## Detailed Components Verification Status

### Package: `caddy-filebrowser-stack` (Reverse Proxy & Remote Workspace)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 109
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy` | Running | OK | None | unknown | ✅ OK |
| `filebrowser` | Running | OK | None | unknown | ✅ OK |

---

### Package: `dns-shield-stack` (DNS & Ad-Blocking Privacy Shield)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `adguard-home` | Running | OK | None | unknown | ✅ OK |
| `unbound` | Running | N/A | None | unknown | ✅ OK |

---

### Package: `monitoring-stack` (Monitoring Stack)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `grafana` | Running | OK | None | unknown | ✅ OK |
| `prometheus` | Running | OK | None | unknown | ✅ OK |

---

### Package: `digital-archive` (Digital Archive & Document Compliance)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `paperless-ngx` | Running | OK | None | unknown | ✅ OK |
| `stirling-pdf` | Running | OK | None | unknown | ✅ OK |
| `actual-budget` | Running | OK | None | unknown | ✅ OK |
| `nocodb` | Running | OK | None | unknown | ✅ OK |

---

### Package: `observability-analytics` (Observability & Privacy Analytics)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `beszel` | Running | OK | None | unknown | ✅ OK |
| `prometheus` | Running | OK | None | unknown | ✅ OK |
| `grafana` | Running | OK | None | unknown | ✅ OK |
| `plausible` | Running | OK | None | unknown | ✅ OK |
| `uptime-kuma` | Running | OK | None | unknown | ✅ OK |

---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** failed
- **Overall Status:** ❌ FAIL

**Error / Failures Message:**
```
Package deployment failed: The deployment sequence failed. See the console logs for detailed execution output.
```

---

### Package: `agile-ops` (Agile Operations & Secure Chat)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `vikunja` | Running | OK | None | unknown | ✅ OK |
| `focalboard` | Running | OK | None | unknown | ✅ OK |
| `gitea` | Running | OK | None | unknown | ✅ OK |
| `conduit` | Running | N/A | None | unknown | ✅ OK |
| `memos` | Running | OK | None | unknown | ✅ OK |

#### Web UI Screenshots:

##### Component: `vikunja`
- **Endpoint:** [http://10.99.0.199:3456](http://10.99.0.199:3456)

![vikunja Web UI](images/test_screenshots/pkg_vikunja_lxc_docker_20260905_151756.png)

##### Component: `focalboard`
- **Endpoint:** [http://10.99.0.199:8099](http://10.99.0.199:8099)

![focalboard Web UI](images/test_screenshots/pkg_focalboard_lxc_docker_20260905_151801.png)

##### Component: `gitea`
- **Endpoint:** [http://10.99.0.199:3000](http://10.99.0.199:3000)

![gitea Web UI](images/test_screenshots/pkg_gitea_lxc_docker_20260905_151808.png)

##### Component: `memos`
- **Endpoint:** [http://10.99.0.199:5230](http://10.99.0.199:5230)

![memos Web UI](images/test_screenshots/pkg_memos_lxc_docker_20260905_151811.png)


---

### Package: `smarthome-stack` (Sovereign Smart Home Hub)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 106
- **IP:** 192.168.178.36
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `homeassistant` | Running | OK | None | unknown | ✅ OK |
| `esphome` | Running | OK | None | unknown | ✅ OK |
| `node-red` | Running | OK | None | unknown | ✅ OK |
| `scrypted` | Running | OK | None | unknown | ✅ OK |

---

### Package: `nextcloud-stack` (Nextcloud Stack)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nextcloud` | Running | OK | None | unknown | ✅ OK |
| `nextcloud-db` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-db-dumper` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-redis` | Running | N/A | None | unknown | ✅ OK |
| `notify-push` | Running | N/A | None | unknown | ✅ OK |

---

### Package: `modern-workplace` (The Modern Sovereign Workplace)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nextcloud` | Running | OK | None | unknown | ✅ OK |
| `nextcloud-db` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-redis` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-db-dumper` | Running | N/A | None | unknown | ✅ OK |
| `notify-push` | Running | N/A | None | unknown | ✅ OK |
| `vaultwarden` | Running | OK | None | unknown | ✅ OK |

---

### Package: `media-stack` (Media Streaming & Servarr Suite)
- **Target:** LXC | **Engine:** DOCKER
- **VMID:** 108
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `jellyfin` | Running | OK | None | unknown | ✅ OK |
| `radarr` | Running | OK | None | unknown | ✅ OK |
| `sonarr` | Running | OK | None | unknown | ✅ OK |
| `prowlarr` | Running | OK | None | unknown | ✅ OK |
| `jellyseerr` | Running | OK | None | unknown | ✅ OK |
| `qbittorrent` | Running | OK | None | unknown | ✅ OK |
| `bazarr` | Running | OK | None | unknown | ✅ OK |

---

### Package: `agile-ops` (Agile Operations & Secure Chat)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `vikunja` | Running | OK | None | unknown | ✅ OK |
| `focalboard` | Running | OK | None | unknown | ✅ OK |
| `gitea` | Running | OK | None | unknown | ✅ OK |
| `conduit` | Running | N/A | None | unknown | ✅ OK |
| `memos` | Running | OK | None | unknown | ✅ OK |

#### Web UI Screenshots:

##### Component: `vikunja`
- **Endpoint:** [http://10.99.0.199:3456](http://10.99.0.199:3456)

![vikunja Web UI](images/test_screenshots/pkg_vikunja_vm_docker_20260905_152055.png)

##### Component: `focalboard`
- **Endpoint:** [http://10.99.0.199:8099](http://10.99.0.199:8099)

![focalboard Web UI](images/test_screenshots/pkg_focalboard_vm_docker_20260905_152103.png)

##### Component: `gitea`
- **Endpoint:** [http://10.99.0.199:3000](http://10.99.0.199:3000)

![gitea Web UI](images/test_screenshots/pkg_gitea_vm_docker_20260905_152107.png)

##### Component: `memos`
- **Endpoint:** [http://10.99.0.199:5230](http://10.99.0.199:5230)

![memos Web UI](images/test_screenshots/pkg_memos_vm_docker_20260905_152111.png)


---

### Package: `caddy-filebrowser-stack` (Reverse Proxy & Remote Workspace)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.147
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy` | Running | N/A | None | unknown | ✅ OK |
| `filebrowser` | Running | OK | None | unknown | ✅ OK |

---

### Package: `digital-archive` (Digital Archive & Document Compliance)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.143
- **Deployment:** success
- **Overall Status:** ❌ FAIL

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `paperless-ngx` | Running | FAIL | None | unknown | ❌ FAILED |
| `stirling-pdf` | Running | FAIL | None | unknown | ❌ FAILED |
| `actual-budget` | Running | OK | None | unknown | ✅ OK |
| `nocodb` | Running | N/A | None | unknown | ✅ OK |

**Error / Failures Message:**
```
Successfully checked 4 components.
```

---

### Package: `dns-shield-stack` (DNS & Ad-Blocking Privacy Shield)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.22
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `adguard-home` | Running | OK | None | unknown | ✅ OK |
| `unbound` | Running | N/A | None | unknown | ✅ OK |

---

### Package: `media-stack` (Media Streaming & Servarr Suite)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.128
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `jellyfin` | Running | OK | None | unknown | ✅ OK |
| `radarr` | Running | OK | None | unknown | ✅ OK |
| `sonarr` | Running | OK | None | unknown | ✅ OK |
| `prowlarr` | Running | OK | None | unknown | ✅ OK |
| `jellyseerr` | Running | N/A | None | unknown | ✅ OK |
| `qbittorrent` | Running | OK | None | unknown | ✅ OK |
| `bazarr` | Running | N/A | None | unknown | ✅ OK |

---

### Package: `modern-workplace` (The Modern Sovereign Workplace)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.175
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nextcloud` | Running | OK | None | unknown | ✅ OK |
| `nextcloud-db` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-redis` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-db-dumper` | Running | N/A | None | unknown | ✅ OK |
| `notify-push` | Running | N/A | None | unknown | ✅ OK |
| `vaultwarden` | Running | OK | None | unknown | ✅ OK |

---

### Package: `monitoring-stack` (Monitoring Stack)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.179
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `grafana` | Running | OK | None | unknown | ✅ OK |
| `prometheus` | Running | OK | None | unknown | ✅ OK |

---

### Package: `nextcloud-stack` (Nextcloud Stack)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.168
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nextcloud` | Running | OK | None | unknown | ✅ OK |
| `nextcloud-db` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-db-dumper` | Running | N/A | None | unknown | ✅ OK |
| `nextcloud-redis` | Running | N/A | None | unknown | ✅ OK |
| `notify-push` | Running | N/A | None | unknown | ✅ OK |

---

### Package: `observability-analytics` (Observability & Privacy Analytics)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.184
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `beszel` | Running | N/A | None | unknown | ✅ OK |
| `prometheus` | Running | OK | None | unknown | ✅ OK |
| `grafana` | Running | OK | None | unknown | ✅ OK |
| `plausible` | Running | OK | None | unknown | ✅ OK |
| `uptime-kuma` | Running | OK | None | unknown | ✅ OK |

---

### Package: `open-webui-ollama` (Open WebUI & Ollama AI Studio)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.178
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ollama` | Running | N/A | None | unknown | ✅ OK |
| `open-webui` | Running | OK | None | unknown | ✅ OK |
| `litellm` | Running | OK | None | unknown | ✅ OK |

---

### Package: `smarthome-stack` (Sovereign Smart Home Hub)
- **Target:** VM | **Engine:** DOCKER
- **VMID:** 104
- **IP:** 192.168.178.172
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `homeassistant` | Running | OK | None | unknown | ✅ OK |
| `esphome` | Running | N/A | None | unknown | ✅ OK |
| `node-red` | Running | N/A | None | unknown | ✅ OK |
| `scrypted` | Running | OK | None | unknown | ✅ OK |

---

### Package: `agile-ops` (Agile Operations & Secure Chat)
- **Target:** LXC | **Engine:** PODMAN
- **VMID:** 104
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `vikunja` | Running | OK | None | unknown | ✅ OK |
| `focalboard` | Running | OK | None | unknown | ✅ OK |
| `gitea` | Running | OK | None | unknown | ✅ OK |
| `conduit` | Running | N/A | None | unknown | ✅ OK |
| `memos` | Running | OK | None | unknown | ✅ OK |

#### Web UI Screenshots:

##### Component: `vikunja`
- **Endpoint:** [http://10.99.0.199:3456](http://10.99.0.199:3456)

![vikunja Web UI](images/test_screenshots/pkg_vikunja_lxc_podman_20260905_162511.png)

##### Component: `focalboard`
- **Endpoint:** [http://10.99.0.199:8099](http://10.99.0.199:8099)

![focalboard Web UI](images/test_screenshots/pkg_focalboard_lxc_podman_20260905_162519.png)

##### Component: `gitea`
- **Endpoint:** [http://10.99.0.199:3000](http://10.99.0.199:3000)

![gitea Web UI](images/test_screenshots/pkg_gitea_lxc_podman_20260905_162523.png)

##### Component: `memos`
- **Endpoint:** [http://10.99.0.199:5230](http://10.99.0.199:5230)

![memos Web UI](images/test_screenshots/pkg_memos_lxc_podman_20260905_162526.png)


---

### Package: `caddy-filebrowser-stack` (Reverse Proxy & Remote Workspace)
- **Target:** LXC | **Engine:** PODMAN
- **VMID:** 104
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `caddy` | Running | OK | None | unknown | ✅ OK |
| `filebrowser` | Running | OK | None | unknown | ✅ OK |

#### Web UI Screenshots:

##### Component: `caddy`
- **Endpoint:** [http://10.99.0.199:80](http://10.99.0.199:80)

![caddy Web UI](images/test_screenshots/pkg_caddy_lxc_podman_20260905_162548.png)

##### Component: `filebrowser`
- **Endpoint:** [http://10.99.0.199:8080](http://10.99.0.199:8080)

![filebrowser Web UI](images/test_screenshots/pkg_filebrowser_lxc_podman_20260905_162551.png)


---

### Package: `agile-ops` (Agile Operations & Secure Chat)
- **Target:** VM | **Engine:** PODMAN
- **VMID:** 104
- **IP:** 10.99.0.199
- **Deployment:** success
- **Overall Status:** ✅ PASS

#### Component Health Status:

| Component ID | Container Running | HTTP UI Port | Log Error (Traceback/Fatal) | Version | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `vikunja` | Running | OK | None | unknown | ✅ OK |
| `focalboard` | Running | OK | None | unknown | ✅ OK |
| `gitea` | Running | OK | None | unknown | ✅ OK |
| `conduit` | Running | N/A | None | unknown | ✅ OK |
| `memos` | Running | OK | None | unknown | ✅ OK |

#### Web UI Screenshots:

##### Component: `vikunja`
- **Endpoint:** [http://10.99.0.199:3456](http://10.99.0.199:3456)

![vikunja Web UI](images/test_screenshots/pkg_vikunja_vm_podman_20260905_152231.png)

##### Component: `focalboard`
- **Endpoint:** [http://10.99.0.199:8099](http://10.99.0.199:8099)

![focalboard Web UI](images/test_screenshots/pkg_focalboard_vm_podman_20260905_152239.png)

##### Component: `gitea`
- **Endpoint:** [http://10.99.0.199:3000](http://10.99.0.199:3000)

![gitea Web UI](images/test_screenshots/pkg_gitea_vm_podman_20260905_152243.png)

##### Component: `memos`
- **Endpoint:** [http://10.99.0.199:5230](http://10.99.0.199:5230)

![memos Web UI](images/test_screenshots/pkg_memos_vm_podman_20260905_152246.png)


---
