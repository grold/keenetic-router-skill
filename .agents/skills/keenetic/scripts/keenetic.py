#!/usr/bin/env python3
"""
Keenetic Router Management CLI & API Client
Supports KeeneticOS 5.x NDW4 (Argon2id + HMAC-SHA3-512) and NDW2 authentication,
session caching, and RCI REST API management.
"""

import sys
import os
import json
import base64
import hmac
import hashlib
import time
import argparse
import socket
import shutil
from pathlib import Path

# Force IPv4 resolution to prevent timeouts on networks without IPv6 routes
try:
    import urllib3.util.connection as urllib_conn
    urllib_conn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("Error: 'requests' library is required. Install via pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
except ImportError:
    Argon2id = None

CONFIG_DIR = Path.home() / ".config" / "keenetic"
CACHE_DIR = Path.home() / ".cache" / "keenetic"
CONFIG_FILE = CONFIG_DIR / "config.json"
SESSION_FILE = CACHE_DIR / "session.json"

DEFAULT_HOST = os.environ.get("KEENETIC_HOST", "http://192.168.1.1")
DEFAULT_LOGIN = os.environ.get("KEENETIC_LOGIN", "")
DEFAULT_PASSWORD = os.environ.get("KEENETIC_PASSWORD", "")


def load_config(target_host=None):
    config = {
        "host": DEFAULT_HOST,
        "login": DEFAULT_LOGIN,
        "password": DEFAULT_PASSWORD,
        "timeout": 15,
        "hosts": {}
    }
    # Load user config file first (~/.config/keenetic/config.json)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "hosts" in data and isinstance(data["hosts"], dict):
                    config["hosts"].update(data["hosts"])
                for k in ["host", "login", "password", "timeout"]:
                    if data.get(k):
                        config[k] = data[k]
        except Exception:
            pass

    # Local directory config override
    local_cfg = Path("config.json")
    if local_cfg.exists():
        try:
            with open(local_cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "hosts" in data and isinstance(data["hosts"], dict):
                    config["hosts"].update(data["hosts"])
                for k in ["host", "login", "password", "timeout"]:
                    if data.get(k):
                        config[k] = data[k]
        except Exception:
            pass

    # Match target host against configured hosts dictionary
    host_to_match = target_host or config["host"]
    clean_host = host_to_match.replace("https://", "").replace("http://", "").strip("/")
    
    if clean_host in config.get("hosts", {}):
        profile = config["hosts"][clean_host]
        config["host"] = profile.get("host", config["host"])
        config["login"] = profile.get("login", config["login"])
        config["password"] = profile.get("password", config["password"])
    elif target_host:
        config["host"] = target_host

    # Environment variables override
    if "KEENETIC_HOST" in os.environ:
        config["host"] = os.environ["KEENETIC_HOST"]
    if "KEENETIC_LOGIN" in os.environ:
        config["login"] = os.environ["KEENETIC_LOGIN"]
    if "KEENETIC_PASSWORD" in os.environ:
        config["password"] = os.environ["KEENETIC_PASSWORD"]

    # Ensure protocol
    if not config["host"].startswith("http://") and not config["host"].startswith("https://"):
        config["host"] = f"https://{config['host']}"

    return config


class KeeneticClient:
    def __init__(self, host=None, login=None, password=None, timeout=15):
        cfg = load_config(target_host=host)
        self.host = host or cfg.get("host", DEFAULT_HOST)
        if not self.host.startswith("http://") and not self.host.startswith("https://"):
            self.host = f"https://{self.host}"
        self.host = self.host.rstrip("/")

        self.login = login or cfg.get("login", DEFAULT_LOGIN)
        self.password = password or cfg.get("password", DEFAULT_PASSWORD)
        self.timeout = timeout or cfg.get("timeout", 15)
        self.session = requests.Session()

    def _get_session_file(self):
        clean_name = self.host.replace("https://", "").replace("http://", "").replace("/", "_").replace(":", "_")
        return CACHE_DIR / f"session_{clean_name}.json"

    def _load_cached_session(self):
        sess_file = self._get_session_file()
        if not sess_file.exists():
            return False
        try:
            with open(sess_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("host") == self.host and data.get("login") == self.login:
                # Max session age 6 hours
                if time.time() - data.get("timestamp", 0) > 21600:
                    return False
                cookies = data.get("cookies", {})
                for k, v in cookies.items():
                    self.session.cookies.set(k, v)
                # Verify session validity with a lightweight call
                test_res = self.session.get(f"{self.host}/rci/show/system", timeout=6, verify=False)
                if test_res.status_code == 200:
                    return True
        except Exception:
            pass
        self.session.cookies.clear()
        return False

    def _save_cached_session(self):
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cookies = self.session.cookies.get_dict()
            sess_file = self._get_session_file()
            with open(sess_file, "w", encoding="utf-8") as f:
                json.dump({
                    "host": self.host,
                    "login": self.login,
                    "cookies": cookies,
                    "timestamp": time.time()
                }, f)
            os.chmod(sess_file, 0o600)
        except Exception:
            pass

    def authenticate(self):
        # 1. Try cached session first
        if self._load_cached_session():
            return True

        if not self.login or not self.password:
            raise ValueError(
                "Router credentials missing. Provide --login and --password, set "
                "KEENETIC_LOGIN and KEENETIC_PASSWORD environment variables, or "
                f"configure {CONFIG_FILE}."
            )

        # 2. Initial GET /auth to retrieve challenge & session cookie
        r0 = self.session.get(f"{self.host}/auth", timeout=self.timeout, verify=False)
        if r0.status_code == 200:
            self._save_cached_session()
            return True

        www_auth = r0.headers.get("www-authenticate", "") or r0.headers.get("WWW-Authenticate", "")
        supports_ndw4 = "x-ndw4" in www_auth

        # 3. NDW4 Authentication (Argon2id + HMAC-SHA3-512)
        if supports_ndw4 and Argon2id is not None:
            if self._authenticate_ndw4(r0):
                self._save_cached_session()
                return True

        # 4. Fallback to NDW2 Authentication (MD5 + SHA-256)
        if self._authenticate_ndw2(r0):
            self._save_cached_session()
            return True

        return False

    def _authenticate_ndw4(self, r0):
        # Phase 1: Client nonce
        client_nonce = os.urandom(16)
        client_nonce_b64 = base64.b64encode(client_nonce).decode('ascii')
        p1_payload = {'login': self.login, 'nonce': client_nonce_b64}
        r1 = self.session.post(f"{self.host}/auth", json=p1_payload, timeout=self.timeout, verify=False)
        ndm_data_raw = r1.headers.get('x-ndm-data') or r1.headers.get('X-NDM-Data')
        if not ndm_data_raw:
            return False

        p1_data = json.loads(base64.b64decode(ndm_data_raw).decode('utf-8'))
        salt_b64 = p1_data['salt']
        server_nonce = p1_data['nonce']
        iter_count = p1_data['iter']
        memcost = p1_data['memcost']
        salt = base64.b64decode(salt_b64)

        # Argon2id Key Derivation
        kdf = Argon2id(salt=salt, length=64, iterations=iter_count, lanes=1, memory_cost=memcost)
        derived_key = kdf.derive(self.password.encode('utf-8'))

        def hmac_sha3(key: bytes, msg: bytes) -> bytes:
            return hmac.new(key, msg, hashlib.sha3_512).digest()

        client_key = hmac_sha3(derived_key, b'NDW4 Interactive Client Key')
        stored_key = hashlib.sha3_512(client_key).digest()
        server_key = hmac_sha3(derived_key, b'NDW4 Interactive Server Key')

        j = f'login1={self.login},nonce1={client_nonce_b64}'
        W = f'iter2={iter_count},memcost2={memcost},nonce2={server_nonce},salt2={salt_b64}'
        J = f'login3={self.login},nonce3={server_nonce}'
        auth_msg4 = f'{j};{W};{J}'.encode('utf-8')

        le = hmac_sha3(stored_key, auth_msg4)
        client_proof = bytes(x ^ y for x, y in zip(client_key, le))
        client_proof_b64 = base64.b64encode(client_proof).decode('ascii')

        # Phase 2: Client proof submission and server signature verification
        p2_payload = {'login': self.login, 'nonce': server_nonce, 'proof': client_proof_b64}
        r2 = self.session.post(f"{self.host}/auth", json=p2_payload, timeout=self.timeout, verify=False)
        ndm_data2_raw = r2.headers.get('x-ndm-data') or r2.headers.get('X-NDM-Data')
        if not ndm_data2_raw:
            return False

        p2_data = json.loads(base64.b64decode(ndm_data2_raw).decode('utf-8'))
        server_sig_b64 = p2_data.get('signature')
        if not server_sig_b64:
            return False

        server_sig = base64.b64decode(server_sig_b64)
        expected_sig = hmac_sha3(server_key, auth_msg4)
        if not hmac.compare_digest(server_sig, expected_sig):
            return False

        # Phase 3: Signature proof confirmation
        s = f'{j};{W};{J};signature4={server_sig_b64}'.encode('utf-8')
        c = hmac_sha3(stored_key, s)
        sig_proof = bytes(x ^ y for x, y in zip(client_key, c))
        sig_proof_b64 = base64.b64encode(sig_proof).decode('ascii')

        p3_payload = {'login': self.login, 'nonce': server_nonce, 'signature-proof': sig_proof_b64}
        r3 = self.session.post(f"{self.host}/auth", json=p3_payload, timeout=self.timeout, verify=False)
        return r3.status_code == 200

    def _authenticate_ndw2(self, r0):
        realm = r0.headers.get("X-NDM-Realm") or ""
        challenge = r0.headers.get("X-NDM-Challenge") or ""
        if not realm or not challenge:
            return False

        md5_hash = hashlib.md5(f"{self.login}:{realm}:{self.password}".encode("utf-8")).hexdigest()
        sha256_hash = hashlib.sha256(f"{challenge}{md5_hash}".encode("utf-8")).hexdigest()

        payload = {"login": self.login, "password": sha256_hash}
        r1 = self.session.post(f"{self.host}/auth", json=payload, timeout=self.timeout, verify=False)
        return r1.status_code == 200

    def rci(self, path, method="GET", data=None):
        if not self.session.cookies:
            if not self.authenticate():
                raise ConnectionError(f"Failed to authenticate with router at {self.host}")

        url = f"{self.host}/rci/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        if method.upper() == "POST":
            resp = self.session.post(url, json=data or {}, headers=headers, timeout=self.timeout, verify=False)
        else:
            resp = self.session.get(url, headers=headers, timeout=self.timeout, verify=False)

        if resp.status_code == 401:
            # Session expired; re-authenticate and retry
            self.session.cookies.clear()
            sess_file = self._get_session_file()
            if sess_file.exists():
                try: sess_file.unlink()
                except Exception: pass
            if self.authenticate():
                if method.upper() == "POST":
                    resp = self.session.post(url, json=data or {}, headers=headers, timeout=self.timeout, verify=False)
                else:
                    resp = self.session.get(url, headers=headers, timeout=self.timeout, verify=False)
            else:
                raise PermissionError(f"Authentication with {self.host} failed")

        if resp.status_code == 200:
            try:
                return resp.json()
            except Exception:
                return resp.text
        else:
            raise RuntimeError(f"RCI request failed: HTTP {resp.status_code} - {resp.text}")

    def get_system(self):
        return self.rci("show/system")

    def get_version(self):
        return self.rci("show/version")

    def get_interfaces(self):
        return self.rci("show/interface")

    def get_devices(self):
        try:
            return self.rci("show/ip/hotspot")
        except Exception:
            return self.rci("show/device-list")

    def get_wifi(self):
        try:
            return self.rci("show/associations")
        except Exception:
            return self.rci("show/interface/WifiMaster0/associations")

    def get_routes(self):
        return self.rci("show/ip/route")

    def get_dhcp(self):
        return self.rci("show/ip/dhcp/bindings")

    def get_logs(self, limit=50):
        try:
            logs = self.rci("show/log")
            if isinstance(logs, list) and limit:
                return logs[-limit:]
            return logs
        except Exception:
            return self.rci("show/audit/log")

    def download_config(self, config_type="startup-config"):
        if not self.session.cookies:
            if not self.authenticate():
                raise ConnectionError(f"Failed to authenticate with router at {self.host}")

        filename = f"{config_type}.txt" if not config_type.endswith(".txt") else config_type
        raw_name = config_type[:-4] if config_type.endswith(".txt") else config_type

        # Try /ci/<filename> endpoint
        url = f"{self.host}/ci/{filename}"
        r = self.session.get(url, verify=False, timeout=self.timeout)
        if r.status_code == 200:
            return r.text

        # Fallback to RCI show/<raw_name>
        try:
            res = self.rci(f"show/{raw_name}")
            if isinstance(res, dict) and "message" in res:
                return "\n".join(res["message"])
        except Exception:
            pass

        raise RuntimeError(f"Failed to download {config_type}: HTTP {r.status_code}")

    def _archive_previous_backup(self, dest: Path):
        """Archives existing backup files into dest/archive/<timestamp>/ before overwriting."""
        startup_file = dest / "startup-config.txt"
        running_file = dest / "running-config.txt"
        info_file = dest / "info.json"

        if not startup_file.exists() and not running_file.exists():
            return None

        # Determine archive folder name from info.json timestamp or file mtime
        ts_str = None
        if info_file.exists():
            try:
                data = json.loads(info_file.read_text(encoding="utf-8"))
                btime = data.get("backup_time")
                if btime:
                    parts = btime.split()
                    if len(parts) >= 2:
                        ts_str = f"{parts[0]}_{parts[1].replace(':', '-')}"
            except Exception:
                pass

        if not ts_str:
            target_f = startup_file if startup_file.exists() else running_file
            mtime = os.path.getmtime(target_f)
            ts_str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(mtime))

        archive_dir = dest / "archive" / ts_str
        archive_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for fname in ["startup-config.txt", "running-config.txt", "backup-config.txt", "default-config.txt", "info.json"]:
            src = dest / fname
            if src.exists() and src.is_file():
                dst = archive_dir / fname
                if not dst.exists() or dst.read_bytes() != src.read_bytes():
                    shutil.copy2(src, dst)
                    copied += 1

        return ts_str if copied > 0 else ts_str

    def backup(self, dest_dir, archive_older=True):
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        results = {}

        # 1. Archive previous backup if present so older backups are preserved
        if archive_older:
            archived_ts = self._archive_previous_backup(dest)
            if archived_ts:
                results["archived_older"] = f"Preserved older backup in archive/{archived_ts}"

        # 2. Download latest startup-config (actual backup)
        try:
            startup = self.download_config("startup-config")
            (dest / "startup-config.txt").write_text(startup, encoding="utf-8")
            results["startup-config"] = f"{len(startup.encode('utf-8'))} bytes (actual)"
        except Exception as e:
            results["startup-config"] = f"Error: {e}"

        # 3. Download latest running-config (actual backup)
        try:
            running = self.download_config("running-config")
            (dest / "running-config.txt").write_text(running, encoding="utf-8")
            results["running-config"] = f"{len(running.encode('utf-8'))} bytes (actual)"
        except Exception as e:
            results["running-config"] = f"Error: {e}"

        # 4. Check router flash for backup-config (older firmware backup if available)
        try:
            backup_cfg = self.download_config("backup-config")
            (dest / "backup-config.txt").write_text(backup_cfg, encoding="utf-8")
            results["backup-config"] = f"{len(backup_cfg.encode('utf-8'))} bytes (actual)"
        except Exception:
            pass

        # 5. Check for default-config (factory default configuration)
        try:
            default_cfg = self.download_config("default-config")
            (dest / "default-config.txt").write_text(default_cfg, encoding="utf-8")
            results["default-config"] = f"{len(default_cfg.encode('utf-8'))} bytes"
        except Exception:
            pass

        # 6. Save current router status & version metadata
        try:
            sys_info = self.get_system()
            ver_info = {}
            try: ver_info = self.get_version()
            except Exception: pass
            meta = {
                "host": self.host,
                "backup_time": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "system": sys_info,
                "version": ver_info
            }
            (dest / "info.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
            results["info"] = "info.json saved (actual)"
        except Exception as e:
            results["info"] = f"Error: {e}"

        # 7. Summarize total archives
        archive_base = dest / "archive"
        if archive_base.exists():
            archives = sorted([d.name for d in archive_base.iterdir() if d.is_dir()])
            results["older_backups"] = f"{len(archives)} older version(s) saved ({', '.join(archives[-3:])})"

        return results

    def reboot(self):
        return self.rci("system/reboot", method="POST", data={})


def format_uptime(seconds):
    if not isinstance(seconds, (int, float)):
        try:
            seconds = int(seconds)
        except Exception:
            return str(seconds)
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if mins: parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def list_backups(base_dir="backups"):
    base = Path(base_dir)
    if not base.exists():
        print(f"No backups directory found at '{base}'.")
        return

    routers = [d for d in sorted(base.iterdir()) if d.is_dir()]
    if not routers:
        print(f"No router backups found in '{base}'.")
        return

    print("=" * 70)
    print(f"Keenetic Router Backups ({base.resolve()})")
    print("=" * 70)
    for rdir in routers:
        startup = rdir / "startup-config.txt"
        running = rdir / "running-config.txt"
        backup_cfg = rdir / "backup-config.txt"
        default_cfg = rdir / "default-config.txt"
        info = rdir / "info.json"
        archive_dir = rdir / "archive"

        btime = "Unknown"
        device = "-"
        fw = "-"
        if info.exists():
            try:
                idata = json.loads(info.read_text(encoding="utf-8"))
                btime = idata.get("backup_time", "Unknown")
                ver = idata.get("version", {})
                sys_inf = idata.get("system", {})
                device = ver.get("device") or sys_inf.get("device") or ver.get("title", "-")
                fw = ver.get("release") or sys_inf.get("release", "-")
            except Exception:
                pass

        print(f"\nRouter: {rdir.name} ({device}, firmware {fw})")
        print(f"  [Actual Backup] ({btime}):")
        if startup.exists():
            print(f"    - startup-config.txt: {startup.stat().st_size:,} bytes")
        if running.exists():
            print(f"    - running-config.txt: {running.stat().st_size:,} bytes")
        if backup_cfg.exists():
            print(f"    - backup-config.txt:  {backup_cfg.stat().st_size:,} bytes")
        if default_cfg.exists():
            print(f"    - default-config.txt: {default_cfg.stat().st_size:,} bytes")

        if archive_dir.exists():
            archives = sorted([d for d in archive_dir.iterdir() if d.is_dir()])
            if archives:
                print(f"  [Older Backups] ({len(archives)} preserved version(s)):")
                for arc in archives:
                    files = [f.name for f in sorted(arc.iterdir()) if f.is_file()]
                    print(f"    * archive/{arc.name}: {', '.join(files)}")
            else:
                print("  [Older Backups]: none archived yet")
        else:
            print("  [Older Backups]: none archived yet")
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Keenetic Router Management CLI & API Client")
    parser.add_argument("--host", help=f"Router host URL (default: {DEFAULT_HOST})")
    parser.add_argument("--login", "-u", help="Login username (or set via KEENETIC_LOGIN or config file)")
    parser.add_argument("--password", "-p", help="Login password (or set via KEENETIC_PASSWORD or config file)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    subparsers.add_parser("status", help="Show router model, KeeneticOS version, CPU, and uptime")
    subparsers.add_parser("system", help="Alias for status")
    subparsers.add_parser("interfaces", help="Show network interfaces and statuses")
    subparsers.add_parser("devices", help="Show connected network devices / hotspot clients")
    subparsers.add_parser("wifi", help="Show Wi-Fi associations and client signal strength")
    subparsers.add_parser("routes", help="Show IP routing table")
    subparsers.add_parser("dhcp", help="Show DHCP bindings")

    log_parser = subparsers.add_parser("logs", help="Show router logs")
    log_parser.add_argument("--limit", type=int, default=50, help="Number of log entries (default: 50)")

    rci_parser = subparsers.add_parser("rci", help="Execute arbitrary RCI path")
    rci_parser.add_argument("path", help="RCI endpoint path (e.g. show/system, show/version)")
    rci_parser.add_argument("--post", help="JSON data for POST request")

    reboot_parser = subparsers.add_parser("reboot", help="Reboot the router")
    reboot_parser.add_argument("--yes", "-y", action="store_true", help="Confirm reboot without prompt")

    backup_parser = subparsers.add_parser("backup", help="Download backup configuration for router(s)")
    backup_parser.add_argument("--all", action="store_true", help="Backup all configured routers in config.json")
    backup_parser.add_argument("--dir", default="backups", help="Destination folder (default: backups)")
    backup_parser.add_argument("--list", "-l", action="store_true", help="List actual and older backups")
    backup_parser.add_argument("--no-archive", action="store_true", help="Skip archiving older backups")

    backups_parser = subparsers.add_parser("backups", help="List actual and older saved backups")
    backups_parser.add_argument("--dir", default="backups", help="Destination folder (default: backups)")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    client = KeeneticClient(host=args.host, login=args.login, password=args.password)

    cmd = args.command
    if cmd in ("status", "system"):
        try:
            sys_info = client.get_system()
            ver_info = {}
            try: ver_info = client.get_version()
            except Exception: pass

            if args.json:
                print(json.dumps({"system": sys_info, "version": ver_info}, indent=2, ensure_ascii=False))
                return

            print("=" * 60)
            print(f"Keenetic Router Status ({client.host})")
            print("=" * 60)
            device_name = ver_info.get("device") or sys_info.get("device") or ver_info.get("title", "Keenetic")
            print(f"Device:       {device_name}")
            print(f"Hostname:     {sys_info.get('hostname', 'Unknown')}")
            rel = ver_info.get("release") or sys_info.get("release", "Unknown")
            print(f"Firmware:     {rel}")
            print(f"Architecture: {ver_info.get('arch', sys_info.get('arch', 'Unknown'))}")
            print(f"CPU Load:     {sys_info.get('cpuload', 0)}%")
            print(f"Memory:       {sys_info.get('memory', '')}")
            uptime = sys_info.get('uptime', 0)
            print(f"Uptime:       {format_uptime(uptime)}")
            print("=" * 60)
        except Exception as e:
            print(f"Error retrieving status: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "interfaces":
        try:
            data = client.get_interfaces()
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            print(f"{'Interface':<22} {'Status':<8} {'IP Address':<18} {'MAC':<18} {'Type':<12}")
            print("-" * 82)
            items = data.items() if isinstance(data, dict) else enumerate(data)
            for k, iface in items:
                name = iface.get('description') or iface.get('name') or k
                state = "UP" if iface.get('state') == 'up' or iface.get('link') == 'up' else "DOWN"
                ip = iface.get('address', iface.get('ip', '-'))
                mac = iface.get('mac', '-')
                itype = iface.get('type', '-')
                print(f"{str(name)[:21]:<22} {state:<8} {str(ip):<18} {str(mac):<18} {str(itype):<12}")
        except Exception as e:
            print(f"Error retrieving interfaces: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "devices":
        try:
            data = client.get_devices()
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            hosts = data.get('host', []) if isinstance(data, dict) else data
            print(f"{'IP':<16} {'MAC':<18} {'Hostname / Name':<25} {'Interface':<14} {'Active':<8}")
            print("-" * 85)
            for d in hosts:
                ip = d.get('ip', '-')
                mac = d.get('mac', '-')
                name = d.get('name') or d.get('hostname') or '-'
                iface = d.get('interface', {}).get('name', '-') if isinstance(d.get('interface'), dict) else str(d.get('interface', '-'))
                active = "YES" if d.get('active') else "NO"
                print(f"{str(ip):<16} {str(mac):<18} {str(name)[:24]:<25} {str(iface):<14} {active:<8}")
        except Exception as e:
            print(f"Error retrieving devices: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "wifi":
        try:
            data = client.get_wifi()
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            stations = data.get('station', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            if not stations:
                print("No active Wi-Fi clients connected.")
                return
            print(f"{'MAC':<18} {'IP':<16} {'SSID / AP':<18} {'RSSI':<8} {'Tx/Rx Speed':<16}")
            print("-" * 80)
            for s in stations:
                mac = s.get('mac', '-')
                ip = s.get('ip', '-')
                ap = s.get('ap', s.get('interface', '-'))
                rssi = f"{s.get('rssi', '-')} dBm"
                speed = f"{s.get('txrate', '-')}/{s.get('rxrate', '-')} Mbps"
                print(f"{str(mac):<18} {str(ip):<16} {str(ap):<18} {str(rssi):<8} {str(speed):<16}")
        except Exception as e:
            print(f"Error retrieving Wi-Fi info: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "routes":
        try:
            data = client.get_routes()
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            routes = data.get('route', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            print(f"{'Destination':<20} {'Gateway':<18} {'Interface':<15} {'Metric':<8}")
            print("-" * 65)
            for r in routes:
                dest = r.get('destination', '-')
                gw = r.get('gateway', '-')
                iface = r.get('interface', '-')
                metric = str(r.get('metric', '-'))
                print(f"{str(dest):<20} {str(gw):<18} {str(iface):<15} {metric:<8}")
        except Exception as e:
            print(f"Error retrieving routes: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "dhcp":
        try:
            data = client.get_dhcp()
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            bindings = data.get('binding', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            print(f"{'IP':<16} {'MAC':<18} {'Hostname':<25} {'Expires':<15}")
            print("-" * 75)
            for b in bindings:
                ip = b.get('ip', '-')
                mac = b.get('mac', '-')
                name = b.get('hostname', '-')
                exp = str(b.get('expires', '-'))
                print(f"{str(ip):<16} {str(mac):<18} {str(name)[:24]:<25} {exp:<15}")
        except Exception as e:
            print(f"Error retrieving DHCP bindings: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "logs":
        try:
            data = client.get_logs(limit=args.limit)
            if args.json:
                print(json.dumps(data, indent=2, ensure_ascii=False))
                return
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        print(f"[{entry.get('time', '')}] {entry.get('message', '')}")
                    else:
                        print(str(entry))
            else:
                print(str(data))
        except Exception as e:
            print(f"Error retrieving logs: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "rci":
        try:
            post_data = None
            if args.post:
                post_data = json.loads(args.post)
            method = "POST" if post_data is not None else "GET"
            res = client.rci(args.path, method=method, data=post_data)
            print(json.dumps(res, indent=2, ensure_ascii=False) if isinstance(res, (dict, list)) else res)
        except Exception as e:
            print(f"Error querying RCI: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd == "reboot":
        if not args.yes:
            ans = input(f"Are you sure you want to reboot the remote Keenetic router ({client.host})? (y/N): ")
            if ans.lower() not in ("y", "yes"):
                print("Reboot cancelled.")
                return
        try:
            client.reboot()
            print("Reboot command dispatched successfully. Router is restarting.")
        except Exception as e:
            print(f"Error sending reboot command: {e}", file=sys.stderr)
            sys.exit(1)

    elif cmd in ("backup", "backups"):
        base_dir = Path(getattr(args, "dir", "backups"))
        if cmd == "backups" or getattr(args, "list", False):
            list_backups(base_dir)
            return

        archive_older = not getattr(args, "no_archive", False)
        if getattr(args, "all", False):
            cfg = load_config()
            hosts_to_backup = list(cfg.get("hosts", {}).keys())
            if not hosts_to_backup:
                hosts_to_backup = [cfg.get("host", DEFAULT_HOST)]
            print(f"Starting backup of {len(hosts_to_backup)} configured routers to '{base_dir}'...")
            for h in hosts_to_backup:
                clean_name = h.replace("https://", "").replace("http://", "").strip("/")
                target_dir = base_dir / clean_name
                print(f"\n[>] Backing up {clean_name} -> {target_dir}")
                try:
                    c = KeeneticClient(host=h)
                    res = c.backup(target_dir, archive_older=archive_older)
                    for item, status in res.items():
                        print(f"    [+] {item}: {status}")
                except Exception as e:
                    print(f"    [-] Failed to backup {clean_name}: {e}", file=sys.stderr)
            print(f"\nBackup complete. All configurations saved in '{base_dir}'.")
        else:
            clean_name = client.host.replace("https://", "").replace("http://", "").strip("/")
            target_dir = base_dir / clean_name
            print(f"Backing up {clean_name} -> {target_dir}...")
            try:
                res = client.backup(target_dir, archive_older=archive_older)
                for item, status in res.items():
                    print(f"  [+] {item}: {status}")
                print(f"Backup saved to '{target_dir}'.")
            except Exception as e:
                print(f"Error backing up router: {e}", file=sys.stderr)
                sys.exit(1)


if __name__ == "__main__":
    main()
