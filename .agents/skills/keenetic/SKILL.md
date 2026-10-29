---
name: keenetic
description: >-
  Manage Keenetic routers locally (192.168.1.1) or remotely via KeenDNS / Cloud relay.
  Use this skill whenever the user asks to inspect or manage their Keenetic router,
  check router status, firmware, CPU or memory load, list connected devices or Wi-Fi clients,
  inspect network interfaces and IP routes, query RCI REST endpoints, inspect router logs,
  or reboot the router.
---

# Keenetic Router Management Skill

This skill provides comprehensive management and monitoring for Keenetic routers (local LAN or remote via KeenDNS / Cloud relay). It connects securely over HTTP/HTTPS using KeeneticOS 5.x NDW4 (Argon2id + HMAC-SHA3-512) and NDW2 authentication with per-host session caching.

--------------------------------------------------------------------------------

## Mandatory Rule: Always Backup Before Any Configuration Changes

> [!IMPORTANT]
> **Pre-Change Backup Requirement**:
> Each time you are asked to make any configuration changes or apply new settings on a router:
> 1. **ALWAYS run a fresh backup BEFORE making any changes**:
>    ```bash
>    python3 keenetic.py --host <target_router> backup
>    ```
> 2. Verify that the backup completes successfully (actual `startup-config.txt` and `running-config.txt` saved, and older version archived).
> 3. Only after the fresh backup is confirmed may you proceed with modifying the configuration.

--------------------------------------------------------------------------------

## Credentials & Configuration

Credentials are loaded from the user's configuration file, environment variables, or CLI parameters:
- **Default Host**: Loaded from `~/.config/keenetic/config.json` (or `KEENETIC_HOST`, defaults to `http://192.168.1.1`)
- **Secondary Hosts**: Configured in `hosts` section of config file (selected via `--host <hostname_or_url>`)
- **Config file**: `~/.config/keenetic/config.json` (permissions `0600`)
- **Session cache**: `~/.cache/keenetic/session_<host>.json` (avoids repeated authentication handshakes)
- **Helper Script**: [`keenetic.py`](./scripts/keenetic.py)

--------------------------------------------------------------------------------

## Common Workflows & Commands

All tasks can be executed using the helper script:

```bash
# Using the workspace script:
python3 keenetic.py <command>
# Or via the skill directory:
python3 .agents/skills/keenetic/scripts/keenetic.py <command>
```

### 1. View Router Status & System Health
Displays device model, KeeneticOS firmware version, hostname, uptime, CPU load, and RAM usage.

```bash
python3 keenetic.py status
```
*(Add `--json` for machine-readable JSON output)*

### 2. List Connected Devices & Hotspot Hosts
Lists all known and currently active network devices, assigned IP addresses, MAC addresses, hostnames, and connected interface:

```bash
python3 keenetic.py devices
```

### 3. Check Wi-Fi Stations & Signal Quality
Displays all connected wireless clients, associated AP/SSID, Wi-Fi band, signal RSSI (dBm), and Tx/Rx negotiation speed:

```bash
python3 keenetic.py wifi
```

### 4. Inspect Network Interfaces
Lists all physical and logical interfaces (WAN/ISP, LAN/Home, Wi-Fi masters, WireGuard VPNs) with link state (UP/DOWN), IP addresses, and MAC addresses:

```bash
python3 keenetic.py interfaces
```

### 5. Check Active IP Routes
Prints the router's active routing table:

```bash
python3 keenetic.py routes
```

### 6. Inspect DHCP Leases
Lists active DHCP client bindings and lease expirations:

```bash
python3 keenetic.py dhcp
```

### 7. View Router System Logs
Fetches recent syslog events from the router:

```bash
python3 keenetic.py logs --limit 50
```

### 8. Query Any Arbitrary RCI Endpoint
Query any KeeneticOS RCI REST path directly:

```bash
# Query system components and packages
python3 keenetic.py rci show/components

# Query ACME SSL certificate status
python3 keenetic.py rci show/acme

# Query mesh Wi-Fi system members
python3 keenetic.py rci show/mws/member
```

### 9. Backup Router Configurations & Historical Archives
Downloads actual/current configuration (`startup-config.txt`, `running-config.txt`, `info.json`, and `backup-config.txt`/`default-config.txt` if present) while automatically preserving older backups in timestamped `archive/<timestamp>/` folders:

```bash
# Backup default router (archives previous backup and saves actual)
python3 keenetic.py backup

# Backup all configured routers at once
python3 keenetic.py backup --all

# List all actual backups and older archived versions
python3 keenetic.py backups
python3 keenetic.py backup --list

# Backup a specific router to a custom folder
python3 keenetic.py --host https://cottage.keenetic.pro backup --dir my_backups
```

#### Backup Directory Structure:
```text
backups/
├── <host>/
│   ├── startup-config.txt        # Actual / latest startup configuration
│   ├── running-config.txt        # Actual / latest running configuration
│   ├── default-config.txt        # Factory default configuration
│   ├── info.json                 # Actual router status, version & backup timestamp
│   └── archive/                  # Older backups preserved across runs
│       ├── 2026-10-29_18-05-37/
│       │   ├── startup-config.txt
│       │   ├── running-config.txt
│       │   └── info.json
│       └── 2026-10-29_18-23-14/
│           ├── startup-config.txt
│           ├── running-config.txt
│           └── info.json
```

### 10. Safely Reboot Router
Triggers a router restart:

```bash
python3 keenetic.py reboot --yes
```

--------------------------------------------------------------------------------

## Example User Prompts

Common prompt patterns that trigger this skill:

- **Status & Health**:
  - *"Check router status and CPU load."*
  - *"Is my router firmware up to date?"*
  - *"Check uptime and memory utilization on the cottage router."*

- **Connected Devices & Wi-Fi**:
  - *"Show all connected devices and their IP/MAC addresses."*
  - *"Check Wi-Fi clients and signal strength (RSSI)."*
  - *"Show active DHCP leases."*

- **Interfaces & Routing**:
  - *"List all network interfaces and check which ones are UP."*
  - *"Show active IP routes on the router."*
  - *"Inspect WireGuard peer status and last handshake time."*

- **Troubleshooting & Maintenance**:
  - *"Show the last 50 router log messages."*
  - *"Run a backup of all my routers."*
  - *"Reboot the router."*

--------------------------------------------------------------------------------

## References

- [Keenetic RCI REST API Manual](./references/rci_api.md)
- [Keenetic CLI Commands Reference](./references/cli_commands.md)
