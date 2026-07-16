# Proxmox Automated Component Testing Report - adguard-home,caddy,conduit,docker-jitsi-meet,filebrowser,frigate,gitlab,heimdall,homarr,homeassistant,homer,jellyfin,nextcloud,nextcloud-db,nextcloud-db-dumper,nextcloud-redis,nginx-proxy-manager,octoprint,organizr,pi-hole,pish-fluffychat-web,portainer,prosody,qbittorrent,radarr,sabnzbd,scrypted,sonarr,traefik,unbound,unifi-controller,uptime-kuma,vaultwarden

**Run Timestamp:** 2026-07-16 13:42:59
**Total Tested:** 33 | **Passed:** 1 | **Failed:** 32

## Results Table

| Component ID | VM ID | IP Address | Deployment | Containers | HTTP | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `adguard-home` | 106 | N/A | failed | Stopped | N/A | **❌ FAIL** |
| `caddy` | 106 | N/A | failed | Stopped | N/A | **❌ FAIL** |
| `conduit` | 106 | N/A | failed | Stopped | N/A | **❌ FAIL** |
| `docker-jitsi-meet` | 106 | N/A | failed | Stopped | N/A | **❌ FAIL** |
| `filebrowser` | 106 | 192.168.178.173 | success | Running | OK | **✅ PASS** |
| `frigate` | 106 | 192.168.178.60 | failed | Stopped | N/A | **❌ FAIL** |
| `gitlab` | 106 | 192.168.178.83 | failed | Stopped | N/A | **❌ FAIL** |
| `heimdall` | 106 | 192.168.178.94 | failed | Stopped | N/A | **❌ FAIL** |
| `homarr` | 106 | 192.168.178.92 | failed | Stopped | N/A | **❌ FAIL** |
| `homeassistant` | 106 | 192.168.178.80 | failed | Stopped | N/A | **❌ FAIL** |
| `homer` | 106 | 192.168.178.194 | failed | Stopped | N/A | **❌ FAIL** |
| `jellyfin` | 106 | 192.168.178.197 | failed | Stopped | N/A | **❌ FAIL** |
| `nextcloud` | 106 | 192.168.178.85 | failed | Stopped | N/A | **❌ FAIL** |
| `nextcloud-db` | 106 | 192.168.178.69 | failed | Stopped | N/A | **❌ FAIL** |
| `nextcloud-db-dumper` | 106 | 192.168.178.189 | failed | Stopped | N/A | **❌ FAIL** |
| `nextcloud-redis` | 106 | 192.168.178.93 | failed | Stopped | N/A | **❌ FAIL** |
| `nginx-proxy-manager` | 106 | 192.168.178.53 | failed | Stopped | N/A | **❌ FAIL** |
| `octoprint` | 106 | 192.168.178.161 | failed | Stopped | N/A | **❌ FAIL** |
| `organizr` | 106 | 192.168.178.186 | failed | Stopped | N/A | **❌ FAIL** |
| `pi-hole` | 106 | 192.168.178.23 | failed | Stopped | N/A | **❌ FAIL** |
| `pish-fluffychat-web` | 106 | 192.168.178.58 | failed | Stopped | N/A | **❌ FAIL** |
| `portainer` | 106 | 192.168.178.103 | failed | Stopped | N/A | **❌ FAIL** |
| `prosody` | 106 | 192.168.178.20 | failed | Stopped | N/A | **❌ FAIL** |
| `qbittorrent` | 106 | 192.168.178.88 | failed | Stopped | N/A | **❌ FAIL** |
| `radarr` | 106 | 192.168.178.115 | failed | Stopped | N/A | **❌ FAIL** |
| `sabnzbd` | 106 | 192.168.178.180 | failed | Stopped | N/A | **❌ FAIL** |
| `scrypted` | 106 | 192.168.178.200 | failed | Stopped | N/A | **❌ FAIL** |
| `sonarr` | 106 | 192.168.178.175 | failed | Stopped | N/A | **❌ FAIL** |
| `traefik` | 106 | 192.168.178.164 | failed | Stopped | N/A | **❌ FAIL** |
| `unbound` | 106 | 192.168.178.67 | failed | Stopped | N/A | **❌ FAIL** |
| `unifi-controller` | 106 | 192.168.178.78 | failed | Stopped | N/A | **❌ FAIL** |
| `uptime-kuma` | 106 | 192.168.178.162 | failed | Stopped | N/A | **❌ FAIL** |
| `vaultwarden` | 106 | 192.168.178.112 | failed | Stopped | N/A | **❌ FAIL** |

## Details & Failures

### Component: `adguard-home`
- **VMID:** 106
- **IP:** N/A
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Container failed to acquire an IP address in time.
```

### Component: `caddy`
- **VMID:** 106
- **IP:** N/A
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Container failed to acquire an IP address in time.
```

### Component: `conduit`
- **VMID:** 106
- **IP:** N/A
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Container failed to acquire an IP address in time.
```

### Component: `docker-jitsi-meet`
- **VMID:** 106
- **IP:** N/A
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Container failed to acquire an IP address in time.
```

### Component: `frigate`
- **VMID:** 106
- **IP:** 192.168.178.60
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.60' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIMRyhAkNAooNOPvVV0pcu7FXr8Bqs+9f2meA9BMNykeN', expected 'AAAAC3NzaC1lZDI1NTE5AAAAINp6+rQ9eJxQffiKMQeig75vD3S1ImoiGUKWyIYjIBif'
```

### Component: `gitlab`
- **VMID:** 106
- **IP:** 192.168.178.83
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.83' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIB+8RJOUbB8qxMIa5kF5qAknFUxFwthFZjF11KqgVQME', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIAG+TJTE0pEOFZKZU3nghekbwj642/cxiDK02mIN98F+'
```

### Component: `heimdall`
- **VMID:** 106
- **IP:** 192.168.178.94
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.94' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAICHu46RqtnXbCg6sfiyh8leHG5edZAJtML/bYLupxnwC', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIG1R5RdTBnm+SpSZQ4DutYxbRk9gAHPbqlAWYu3cLWrY'
```

### Component: `homarr`
- **VMID:** 106
- **IP:** 192.168.178.92
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.92' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAICraCiKVkY3UjOCgqyhoLpQUmUtlgwNoqv9+4hteHYCk', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIEqdZKgxATmY39PpqYx+KXD4J9lvL4sk5usNOU1xrvd9'
```

### Component: `homeassistant`
- **VMID:** 106
- **IP:** 192.168.178.80
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.80' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIFB83qeHKJwMtQePr/DAgLfDJIQo+4dWefqluTFW9Y8T', expected 'AAAAC3NzaC1lZDI1NTE5AAAAILp72VdRBZwHXeX2qD623TBZqMFnE6yoHkyEXxYYgmf/'
```

### Component: `homer`
- **VMID:** 106
- **IP:** 192.168.178.194
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `jellyfin`
- **VMID:** 106
- **IP:** 192.168.178.197
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `nextcloud`
- **VMID:** 106
- **IP:** 192.168.178.85
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `nextcloud-db`
- **VMID:** 106
- **IP:** 192.168.178.69
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.69' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIPqmNcsZMUxoDXG2qvrusWmmTSPvob6FF4oTGARTllTN', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIMEX9JpKEGVQaconhmNzfNyVuS1HcKd9H9wP1yJNmcj9'
```

### Component: `nextcloud-db-dumper`
- **VMID:** 106
- **IP:** 192.168.178.189
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.189' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIPlfz/6N34jfI/ntS/iZv/3T86iX5VuUKeemqrwSsPF1', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIIn+TKIZVlsOexG8OUnb+dpy29IGJY/0sJpCShyMZqhg'
```

### Component: `nextcloud-redis`
- **VMID:** 106
- **IP:** 192.168.178.93
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.93' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIPGDTFHTuJWlej4RGZJHgAJ2siedLxxNfFIc3SbPvlTD', expected 'AAAAC3NzaC1lZDI1NTE5AAAAINy09/+NqXHLZx6vwHz24lHICC0b0vuPxOkZmuype5ub'
```

### Component: `nginx-proxy-manager`
- **VMID:** 106
- **IP:** 192.168.178.53
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.53' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIMA7CREGLdLQjn6jych7GvIjVJeJu1QpDAh7+9mV0BIh', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIAxeYvP0K78kq4CjKhVh1qlity782YDCbJp88V67VDRn'
```

### Component: `octoprint`
- **VMID:** 106
- **IP:** 192.168.178.161
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `organizr`
- **VMID:** 106
- **IP:** 192.168.178.186
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `pi-hole`
- **VMID:** 106
- **IP:** 192.168.178.23
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.23' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIKTQJRss/Sd4XBLp/UQ9Vis7+h8Da4EknYu24vilzXhH', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIGySu6z+3dpp431TtvoW2f7TQAuYytSqNxGY26mO6UIH'
```

### Component: `pish-fluffychat-web`
- **VMID:** 106
- **IP:** 192.168.178.58
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `portainer`
- **VMID:** 106
- **IP:** 192.168.178.103
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `prosody`
- **VMID:** 106
- **IP:** 192.168.178.20
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.20' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIEv3SYPFjg5SOvGDinrRCv5J7YORSrxxixgO+EzKSbK0', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIL+AmlCx8FepNjp2jj/u+a6OrGcYjcRWHpVsKcgCTtns'
```

### Component: `qbittorrent`
- **VMID:** 106
- **IP:** 192.168.178.88
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.88' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIAo5MkG7d5PfDwICyaJDq60Cyl5m5OhYlU1aYN4onFFH', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIKq9OvGxZQjAI9Ufa2zM6xnZxHbBnHJlGqwHQosZ2jtR'
```

### Component: `radarr`
- **VMID:** 106
- **IP:** 192.168.178.115
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.115' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIMTH9z2ukmHpRnOGyhvfuOGRFWlxR0Sv8wmQO+y9DzCs', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIFgiiNoc+tl8Ddt+HXmN7pZ+3XmUKRfA4cdBWbEK4eIO'
```

### Component: `sabnzbd`
- **VMID:** 106
- **IP:** 192.168.178.180
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `scrypted`
- **VMID:** 106
- **IP:** 192.168.178.200
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.200' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAINDtX1wJybxnl6b1MIdfOWeCijH6PMfn7LAnBlZkM3Tk', expected 'AAAAC3NzaC1lZDI1NTE5AAAAIJ+Wk+FpWVyeNGJGmMERV1KOyAlqGuHWVnzP+x3BPMYS'
```

### Component: `sonarr`
- **VMID:** 106
- **IP:** 192.168.178.175
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `traefik`
- **VMID:** 106
- **IP:** 192.168.178.164
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `unbound`
- **VMID:** 106
- **IP:** 192.168.178.67
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `unifi-controller`
- **VMID:** 106
- **IP:** 192.168.178.78
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `uptime-kuma`
- **VMID:** 106
- **IP:** 192.168.178.162
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: timed out
```

### Component: `vaultwarden`
- **VMID:** 106
- **IP:** 192.168.178.112
- **Deployment Outcome:** failed
- **Error / Logs:**
```
Failed to connect to LXC over SSH: Host key for server '192.168.178.112' does not match: got 'AAAAC3NzaC1lZDI1NTE5AAAAIJzv5Lde/5Xpn2ln8TPVDOgRuZMDejnGUwhRBRssFEy2', expected 'AAAAC3NzaC1lZDI1NTE5AAAAICI9Wr81xXLOGuEluu7n0s2ZilsB1uiAiCPhqiNpty0L'
```
