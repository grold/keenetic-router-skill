# Keenetic CLI Command Reference

KeeneticOS features a Cisco-like command line interface accessible via Telnet (port 23) or SSH (port 22).

## Accessing the CLI

```bash
# Telnet (local network)
telnet 192.168.1.1
```

## Useful Monitoring Commands

```text
show version              # Display KeeneticOS version and uptime
show system               # Display system information, memory, and CPU usage
show interface            # Show interface statuses and IP configurations
show interface stat       # Show packet and byte throughput per interface
show ip hotspot           # List connected hosts and active devices
show associations         # Show Wi-Fi clients and signal metrics
show ip route             # Show routing table
show log                  # Display system log buffer
show running-config       # Print current router configuration
```

## Management Commands

```text
system reboot             # Reboot the router
system configuration save # Save running configuration to startup
system default            # Reset router to factory defaults (caution)
```

## Interface Configuration

```text
interface <name> up       # Bring up an interface
interface <name> down     # Shut down an interface
```

## Brute-Force Lockout Policy Adjustments

```text
ip http lockout-policy <threshold> [<duration>] [<window>]
# Example: 10 attempts, 5 minute lockout, 3 minute observation window:
ip http lockout-policy 10 5 3
system configuration save
```
