# Keenetic RCI API Reference

The Keenetic Router Control Interface (RCI) is a RESTful API provided by KeeneticOS. It exposes router monitoring, interface statistics, DHCP and device tracking, Wi-Fi parameters, and system controls.

## Base URLs & Authentication

- Cloud URL: `https://<domain>.keenetic.pro/rci/`
- Local URL: `http://192.168.1.1/rci/` or `https://192.168.1.1/rci/`
- Authentication Endpoint: `/auth`
  - **NDW4 (KeeneticOS 5.2+)**: SCRAM-like 3-phase Argon2id + HMAC-SHA3-512 authentication.
  - **NDW2 (Legacy)**: Challenge-response MD5 + SHA-256.

## Common `show` Endpoints (GET `/rci/<path>`)

### System & Health
- `show/system`: Model name, hostname, firmware release, uptime, CPU load, memory usage.
- `show/version`: Firmware version details and build timestamp.
- `show/components`: Installed components, packages, and upgrade availability.
- `show/log`: Recent system syslog events.
- `show/audit/log`: Security audit log entries.
- `show/clock`: Current router time, NTP sync status, and timezone.

### Interfaces & Traffic
- `show/interface`: Complete list of all physical and logical interfaces (`ISP`, `Home`, `WifiMaster0`, `WifiMaster1`, VPN, WireGuard, OpenVPN, PPPoE), IP addresses, link speed, and MAC addresses.
- `show/interface/stat`: Byte and packet statistics for all network interfaces.
- `show/ip/route`: Active routing table (destinations, gateways, metrics).

### Connected Devices & Network Clients
- `show/ip/hotspot`: Registered and DHCP-assigned clients, hostnames, IP addresses, MAC addresses, active online status, and traffic.
- `show/device-list`: Detailed topology and device classification list.
- `show/ip/dhcp/bindings`: Active DHCP leases with expiration times.

### Wireless (Wi-Fi)
- `show/associations`: List of connected Wi-Fi stations across all access points, including RSSI (signal strength), Tx/Rx rates, and Wi-Fi band.
- `show/interface/WifiMaster0/associations`: 2.4 GHz client associations.
- `show/interface/WifiMaster1/associations`: 5 GHz client associations.
- `show/channels`: Wi-Fi channel utilization and congestion analysis.

### Mesh Wi-Fi (MWS)
- `show/mws/member`: Wi-Fi system extender nodes and mesh status.
- `show/mws/candidate`: Detected extender nodes available for pairing.

## Action & Control Endpoints (POST `/rci/<path>`)

### System Control
- `system/reboot`: Reboot the router (`{}`).
- `system/configuration/save`: Save startup configuration.

### Batch Commands (POST `/rci/`)
You can send multiple commands in a single batch request:
```json
[
  {"show": {"system": {}}},
  {"show": {"interface": {}}}
]
```
