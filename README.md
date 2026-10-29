# Keenetic Router Management CLI & Universal AI Agent Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![KeeneticOS: 3.x / 4.x / 5.x](https://img.shields.io/badge/KeeneticOS-3.x%20--%205.x-teal.svg)](https://keenetic.com)
[![Skills.sh](https://img.shields.io/badge/skills.sh-grold%2Fkeenetic--router--skill-black)](https://skills.sh)

A powerful CLI tool, Python client library, and **Universal AI Agent Skill** for managing Keenetic routers locally (e.g. `http://192.168.1.1`) or remotely over KeenDNS / Cloud relay (`https://<name>.keenetic.pro` / `https://<name>.keenetic.link`).

Compatible with **Claude Code**, **Cursor**, **Antigravity**, **Windsurf**, **Codex / ChatGPT**, and any agent adhering to the open [skills.sh](https://skills.sh) specification.

Supports **KeeneticOS 5.x NDW4** (SCRAM-style Argon2id + HMAC-SHA3-512) and **NDW2** authentication with automatic session cookie caching and brute-force lockout protection.

---

## ⚡ Quick Install (Any AI Agent)

Install directly into your current project for all detected coding agents using the [skills.sh](https://skills.sh) CLI:

```bash
npx skills add grold/keenetic-router-skill
```

Or install globally across all projects on your system:

```bash
npx skills add grold/keenetic-router-skill -g
```

---

## Features

- **Universal AI Agent Skill**: Open `SKILL.md` specification with prompt triggers, workflows, and runbooks compatible with Claude Code, Cursor, Windsurf, Antigravity, and other assistants.
- **System Health**: Check hardware model, KeeneticOS firmware release, CPU and memory load, and system uptime.
- **Device & Hotspot Tracking**: List active network clients, MAC addresses, assigned IP leases, and link types.
- **Wireless Diagnostics**: Real-time Wi-Fi client association list, band (2.4 GHz / 5 GHz), RSSI signal strength (dBm), and Tx/Rx negotiation speeds.
- **Interface & Route Inspection**: Monitor physical ports (ISP, Home LAN) and virtual tunnels (WireGuard, OpenVPN, SSTP) alongside the active IP routing table.
- **RCI REST Explorer**: Directly execute arbitrary queries against the KeeneticOS RCI REST API (`show/components`, `show/acme`, `show/mws/member`, etc.).
- **Automated Backup & Archive**: Download running and startup configs, preserving older versions in timestamped archives (`archive/<timestamp>/`).
- **Safe Reboot**: Reboot routers remotely with safety confirmation.

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

### Agent-Specific Installation

#### 1. Claude Code
```bash
npx skills add grold/keenetic-router-skill --agent claude-code
```
*(Or add `-g` for global installation)*

#### 2. Cursor
```bash
npx skills add grold/keenetic-router-skill --agent cursor
```

#### 3. Antigravity / Gemini CLI
```bash
npx skills add grold/keenetic-router-skill --agent antigravity
```
*(Or copy `.agents/skills/keenetic/` directly into your workspace or `~/.gemini/config/skills/`)*

#### 4. Windsurf / Codex / Other Assistants
```bash
npx skills add grold/keenetic-router-skill -a '*'
```
*(Installs to all agents detected in the project environment)*

---

### Standalone CLI Tool (Without an AI Agent)

Clone the repository to any directory:

```bash
git clone https://github.com/grold/keenetic-router-skill.git
cd keenetic-router-skill
chmod +x keenetic.py
sudo ln -s "$(pwd)/keenetic.py" /usr/local/bin/keenetic
```

---

## Configuration

Credentials and router targets are stored in `~/.config/keenetic/config.json`. This keeps your credentials separate from code and prevents accidental git commits.

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

## How to Use (CLI)

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

## Example Prompts for AI Agents

Once installed, you can talk to your coding assistant (Claude Code, Cursor, Antigravity, etc.) in natural language:

### System Status & Health
- *"Check the current health, CPU load, and uptime on my router."*
- *"Are all my secondary routers (cottage and office) reachable? Show a status summary table."*
- *"Check what version of KeeneticOS is running and if any updates are available."*

### Wi-Fi Diagnostics & Client Tracking
- *"List all connected Wi-Fi clients along with their band (2.4/5GHz), RSSI signal in dBm, and connection speed."*
- *"Are there any unknown or unregistered devices on my network right now?"*
- *"Which device on the network has the IP 192.168.1.45?"*

### Network Interfaces & VPN Management
- *"Show all active network interfaces and their link state (up/down)."*
- *"Check the handshake status and transferred bytes for WireGuard tunnel peers."*
- *"Add a new WireGuard client called 'phone' with IP 10.0.0.5 on interface Wireguard3."*
- *"Configure policy routing to direct traffic for domain.com through the WireGuard tunnel."*

### Troubleshooting, Logs & Backups
- *"Backup all configured routers right now."*
- *"Show the last 50 syslog messages and see if there are any connection drops or DNS errors."*
- *"Safely reboot the router after creating a fresh backup."*

---

## Safety Rule for AI Agents

When using this skill with any AI coding agent, the workspace includes a mandatory safety rule in [`AGENTS.md`](./AGENTS.md):

> **Mandatory Pre-Change Backup**:
> Whenever an agent is instructed to make or test any configuration changes on any Keenetic router (via RCI, CLI, or API), it **must** run `python3 keenetic.py --host <target_router> backup` and verify that the backup succeeded before modifying any setting.

---

## License

This project is open source and available under the [MIT License](LICENSE).
