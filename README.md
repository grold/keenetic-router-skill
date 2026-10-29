# Keenetic Router Management CLI & Antigravity Agent Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![KeeneticOS: 3.x / 4.x / 5.x](https://img.shields.io/badge/KeeneticOS-3.x%20--%205.x-teal.svg)](https://keenetic.com)

A powerful CLI tool, Python client library, and AI Agent skill for managing Keenetic routers locally (e.g. `http://192.168.1.1`) or remotely over KeenDNS / Cloud relay (`https://<name>.keenetic.pro` / `https://<name>.keenetic.link`).

Supports **KeeneticOS 5.x NDW4** (SCRAM-style Argon2id + HMAC-SHA3-512) and **NDW2** authentication with automatic session cookie caching and brute-force lockout protection.

---

## Features

- **System Health**: Check hardware model, KeeneticOS firmware release, CPU and memory load, and system uptime.
- **Device & Hotspot Tracking**: List active network clients, MAC addresses, assigned IP leases, and link types.
- **Wireless Diagnostics**: Real-time Wi-Fi client association list, band (2.4 GHz / 5 GHz), RSSI signal strength (dBm), and Tx/Rx negotiation speeds.
- **Interface & Route Inspection**: Monitor physical ports (ISP, Home LAN) and virtual tunnels (WireGuard, OpenVPN, SSTP) alongside the active IP routing table.
- **RCI REST Explorer**: Directly execute arbitrary queries against the KeeneticOS RCI REST API (`show/components`, `show/acme`, `show/mws/member`, etc.).
- **Automated Backup & Archive**: Download running and startup configs, preserving older versions in timestamped archives (`archive/<timestamp>/`).
- **Antigravity AI Skill**: Fully documented runbook and tool specifications for autonomous AI coding agents (Antigravity).

---

## Installation

### Prerequisites

- Python 3.8 or newer
- `requests` library
- `cryptography` library (required for KeeneticOS 5.x Argon2id authentication)

Install the required Python packages:

```bash
pip install requests cryptography
```

---

### Method 1: Standalone CLI Tool

Clone the repository to any directory:

```bash
git clone https://github.com/your-username/keenetic-skill.git
cd keenetic-skill
```

Optional: make the CLI tool executable globally by symlinking it:

```bash
chmod +x keenetic.py
sudo ln -s "$(pwd)/keenetic.py" /usr/local/bin/keenetic
```

---

### Method 2: As an Antigravity AI Agent Skill

You can add this skill to your Antigravity agent in two ways:

#### A. Project-Specific Skill (Recommended for teams)
Copy the skill into your project's workspace:

```bash
mkdir -p .agents/skills/
cp -r /path/to/keenetic-skill/.agents/skills/keenetic .agents/skills/
```

#### B. Global User Skill (Available across all workspaces)
Install the skill into your global Antigravity configuration directory:

```bash
mkdir -p ~/.gemini/config/skills/
cp -r /path/to/keenetic-skill/.agents/skills/keenetic ~/.gemini/config/skills/
```

Once installed, your agent will automatically discover the skill and be able to inspect and configure your routers.

---

## Configuration

Credentials and targets are stored in `~/.config/keenetic/config.json`. This keeps your credentials separate from code and prevents accidental commits.

1. **Create the configuration directory and template**:

   ```bash
   mkdir -p ~/.config/keenetic
   cp config.example.json ~/.config/keenetic/config.json
   chmod 600 ~/.config/keenetic/config.json
   ```

2. **Edit `~/.config/keenetic/config.json`**:

   ```json
   {
     "host": "http://192.168.1.1",
     "login": "admin",
     "password": "your_secure_password",
     "timeout": 15,
     "hosts": {
       "home": {
         "host": "http://192.168.1.1",
         "login": "admin",
         "password": "your_secure_password"
       },
       "cottage": {
         "host": "https://cottage.keenetic.pro",
         "login": "admin",
         "password": "your_remote_password"
       },
       "office": {
         "host": "https://office.keenetic.link",
         "login": "admin",
         "password": "your_office_password"
       }
     }
   }
   ```

3. **Environment Variables (Optional)**:
   You can also override credentials via environment variables:
   ```bash
   export KEENETIC_HOST="https://cottage.keenetic.pro"
   export KEENETIC_LOGIN="admin"
   export KEENETIC_PASSWORD="your_password"
   ```

---

## How to Use

### 1. View System Status
Displays model, KeeneticOS version, CPU utilization, and RAM:

```bash
# Default router from config
python3 keenetic.py status

# Target a secondary router configured in hosts
python3 keenetic.py --host cottage status
python3 keenetic.py --host https://office.keenetic.link status

# Raw JSON output
python3 keenetic.py status --json
```

### 2. Connected Devices & Wi-Fi Diagnostics
Inspect active LAN hosts and wireless reception:

```bash
# List all active and registered network devices
python3 keenetic.py devices

# Show Wi-Fi clients with RSSI signal (dBm), AP, and link speed
python3 keenetic.py wifi
```

### 3. Network Interfaces & Routing Table
Monitor ports, VPN tunnels, and IP routes:

```bash
# Show physical WAN/LAN ports and virtual interfaces (WireGuard, SSTP)
python3 keenetic.py interfaces

# Print the active IPv4 routing table
python3 keenetic.py routes

# Check current DHCP leases
python3 keenetic.py dhcp
```

### 4. Router Logs & RCI REST Queries
Query syslog events or any internal KeeneticOS endpoint:

```bash
# Fetch last 50 syslog messages
python3 keenetic.py logs --limit 50

# Query arbitrary RCI endpoints directly
python3 keenetic.py rci show/version
python3 keenetic.py rci show/components
python3 keenetic.py rci show/ip/policy
```

### 5. Automated Backups & Safe Changes
Backup configurations before applying any changes:

```bash
# Backup default router (preserves older backups in archive/)
python3 keenetic.py backup

# Backup all configured routers at once
python3 keenetic.py backup --all

# List all current backups and historical snapshots
python3 keenetic.py backups

# Safely reboot router
python3 keenetic.py reboot --yes
```

#### Backup Directory Structure:
```text
backups/
├── <host>/
│   ├── startup-config.txt        # Latest startup configuration
│   ├── running-config.txt        # Latest running configuration
│   ├── default-config.txt        # Factory default configuration
│   ├── info.json                 # Device model, version & metadata
│   └── archive/                  # Historical backups preserved per run
│       ├── 2026-10-29_18-05-37/
│       └── 2026-10-29_19-22-44/
```

---

## Safety Rule for AI Agents

When using this skill with AI coding agents (Antigravity / Gemini), the workspace includes a mandatory rule in [`AGENTS.md`](./AGENTS.md):

> **Mandatory Pre-Change Backup**:
> Whenever an agent is instructed to make or test any configuration changes on any Keenetic router (via RCI, CLI, or API), it **must** run `python3 keenetic.py --host <target_router> backup` and verify that the backup succeeded before modifying any setting.

---

## License

This project is open source and available under the [MIT License](LICENSE).
