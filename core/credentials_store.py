import json
import base64
from pathlib import Path
from typing import Tuple
from config import REMEMBER_ME_FILE, AVANTURE_CREDS_FILE

class CredentialsStore:
    """Safely stores and retrieves remembered login credentials for the desktop app."""

    @staticmethod
    def save(username: str, password: str):
        try:
            # Obfuscate strings for simple local file storage
            data = {
                "u": base64.b64encode(username.encode("utf-8")).decode("utf-8"),
                "p": base64.b64encode(password.encode("utf-8")).decode("utf-8"),
                "remember": True
            }
            with open(REMEMBER_ME_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    @staticmethod
    def load() -> Tuple[str, str, bool]:
        """Returns (username, password, is_remembered)."""
        if not REMEMBER_ME_FILE.exists():
            return "", "", False

        try:
            with open(REMEMBER_ME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            u = base64.b64decode(data.get("u", "").encode("utf-8")).decode("utf-8")
            p = base64.b64decode(data.get("p", "").encode("utf-8")).decode("utf-8")
            return u, p, True
        except Exception:
            return "", "", False

    @staticmethod
    def clear():
        try:
            if REMEMBER_ME_FILE.exists():
                REMEMBER_ME_FILE.unlink()
        except Exception:
            pass


DEFAULT_PROXY_URL = "http://14a17d6e203a3:c60c979201@163.5.113.150:12323"

class AvantureCredentialsStore:
    """Stores and retrieves dynamic Avanture account profiles, proxy settings, and listing details."""

    DEFAULT_PROFILE = {
        "profile_name": "Profile 1 (venusxxx)",
        "username": "venusxxx",
        "password": "123Fandelux456.",
        "proxy": DEFAULT_PROXY_URL,
        "proxy_protocol": "HTTP",
        "proxy_host": "163.5.113.150",
        "proxy_port": "12323",
        "proxy_login": "14a17d6e203a3",
        "proxy_password": "c60c979201",
        "proxy_name": "Venus",
        "proxy_change_ip_link": "",
        "title": "A relaxed evening for two in Ljubljana",
        "category": "She seeks him (Ona išče njega)",
        "description": "Looking for a pleasant, mature company for dinner, wine, and casual conversation. Polite and respectful gentleman.",
        "country": "Slovenia",
        "state": "Osrednjeslovenska",
        "city": "Ljubljana",
        "registration_number": "",
        "image_path": ""
    }

    @staticmethod
    def parse_proxy_components(proxy_str: str) -> dict:
        """Parses any proxy URI or host:port:user:pass string into component dictionary."""
        res = {
            "protocol": "HTTP",
            "host": "",
            "port": "",
            "login": "",
            "password": "",
            "name": "",
            "change_ip_link": ""
        }
        if not proxy_str or not proxy_str.strip():
            return res

        clean = proxy_str.strip()
        parts = clean.split(":")
        if len(parts) == 4 and "://" not in clean:
            res["host"] = parts[0]
            res["port"] = parts[1]
            res["login"] = parts[2]
            res["password"] = parts[3]
            return res

        if "://" not in clean:
            clean = "http://" + clean

        try:
            import urllib.parse
            parsed = urllib.parse.urlsplit(clean)
            if parsed.scheme:
                scheme_upper = parsed.scheme.upper()
                if scheme_upper in ["HTTP", "SOCKS4", "SOCKS5", "SSH"]:
                    res["protocol"] = scheme_upper
                elif scheme_upper == "HTTPS":
                    res["protocol"] = "HTTP"
            if parsed.hostname:
                res["host"] = parsed.hostname
            if parsed.port:
                res["port"] = str(parsed.port)
            if parsed.username:
                res["login"] = urllib.parse.unquote(parsed.username)
            if parsed.password:
                res["password"] = urllib.parse.unquote(parsed.password)
        except Exception:
            pass
        return res

    @staticmethod
    def build_proxy_url(protocol: str, host: str, port: str, login: str = "", password: str = "") -> str:
        """Builds a standard proxy URL from individual components."""
        host = host.strip()
        port = port.strip()
        if not host:
            return ""
        proto = (protocol or "HTTP").strip().lower()
        if proto not in ["http", "socks4", "socks5", "ssh"]:
            proto = "http"
        port_part = f":{port}" if port else ""
        if login.strip() and password.strip():
            import urllib.parse
            u = urllib.parse.quote(login.strip(), safe="")
            p = urllib.parse.quote(password.strip(), safe="")
            return f"{proto}://{u}:{p}@{host}{port_part}"
        elif login.strip():
            import urllib.parse
            u = urllib.parse.quote(login.strip(), safe="")
            return f"{proto}://{u}@{host}{port_part}"
        return f"{proto}://{host}{port_part}"

    @staticmethod
    def normalize_profile(item: dict, idx: int = 0) -> dict:
        def_prof = dict(AvantureCredentialsStore.DEFAULT_PROFILE)
        if not isinstance(item, dict):
            return dict(def_prof)

        u = item.get("username", "")
        if not u and item.get("u"):
            try:
                u = base64.b64decode(item["u"].encode("utf-8")).decode("utf-8")
            except Exception:
                pass

        p = item.get("password", "")
        if not p and item.get("p"):
            try:
                p = base64.b64decode(item["p"].encode("utf-8")).decode("utf-8")
            except Exception:
                pass

        label = item.get("profile_name", "").strip()
        if not label:
            label = f"Profile {idx + 1} ({u})" if u else f"Profile {idx + 1}"

        # Granular proxy handling
        raw_proxy = item.get("proxy", "")
        parsed_comp = AvantureCredentialsStore.parse_proxy_components(raw_proxy)

        proto = item.get("proxy_protocol") or parsed_comp.get("protocol") or "HTTP"
        host = item.get("proxy_host") or parsed_comp.get("host") or ""
        port = str(item.get("proxy_port") or parsed_comp.get("port") or "")
        login = item.get("proxy_login") or parsed_comp.get("login") or ""
        pwd = item.get("proxy_password") or parsed_comp.get("password") or ""
        p_name = item.get("proxy_name") or parsed_comp.get("name") or ""
        change_link = item.get("proxy_change_ip_link") or ""

        if not host and not raw_proxy:
            # Fall back to default proxy
            def_comp = AvantureCredentialsStore.parse_proxy_components(DEFAULT_PROXY_URL)
            proto = def_comp["protocol"]
            host = def_comp["host"]
            port = def_comp["port"]
            login = def_comp["login"]
            pwd = def_comp["password"]
            p_name = "Venus"

        built_proxy = AvantureCredentialsStore.build_proxy_url(proto, host, port, login, pwd) if host else raw_proxy

        return {
            "profile_name": label,
            "username": u,
            "password": p,
            "proxy": built_proxy,
            "proxy_protocol": proto,
            "proxy_host": host,
            "proxy_port": port,
            "proxy_login": login,
            "proxy_password": pwd,
            "proxy_name": p_name,
            "proxy_change_ip_link": change_link,
            "title": item.get("title", def_prof["title"]),
            "category": item.get("category", def_prof["category"]),
            "description": item.get("description", def_prof["description"]),
            "country": item.get("country", def_prof["country"]),
            "state": item.get("state", def_prof["state"]),
            "city": item.get("city", def_prof["city"]),
            "registration_number": item.get("registration_number", ""),
            "image_path": item.get("image_path", "")
        }

    @staticmethod
    def save(profiles_or_profile=None):
        try:
            if isinstance(profiles_or_profile, dict):
                profs = [profiles_or_profile]
            elif isinstance(profiles_or_profile, list):
                profs = profiles_or_profile
            else:
                profs = [dict(AvantureCredentialsStore.DEFAULT_PROFILE)]

            normalized = [
                AvantureCredentialsStore.normalize_profile(p, idx=i) 
                for i, p in enumerate(profs)
            ]
            if not normalized:
                normalized = [dict(AvantureCredentialsStore.DEFAULT_PROFILE)]

            first = normalized[0]
            saved = {
                "profiles": normalized,
                "accounts": normalized,
                "username": first["username"],
                "password": first["password"],
                "proxy": first["proxy"],
                "proxy_protocol": first.get("proxy_protocol", "HTTP"),
                "proxy_host": first.get("proxy_host", ""),
                "proxy_port": first.get("proxy_port", ""),
                "proxy_login": first.get("proxy_login", ""),
                "proxy_password": first.get("proxy_password", ""),
                "proxy_name": first.get("proxy_name", ""),
                "proxy_change_ip_link": first.get("proxy_change_ip_link", ""),
                "title": first["title"],
                "category": first["category"],
                "description": first["description"],
                "country": first["country"],
                "state": first["state"],
                "city": first["city"],
                "registration_number": first["registration_number"],
                "image_path": first["image_path"]
            }

            with open(AVANTURE_CREDS_FILE, "w", encoding="utf-8") as f:
                json.dump(saved, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def load() -> Tuple[list, str, str]:
        """Loads all dynamic profiles. Returns (profiles_list, default_proxy, default_image_path)."""
        def_prof = dict(AvantureCredentialsStore.DEFAULT_PROFILE)
        if not AVANTURE_CREDS_FILE.exists():
            return [dict(def_prof)], def_prof["proxy"], ""

        try:
            with open(AVANTURE_CREDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_list = []
            if "profiles" in data and isinstance(data["profiles"], list) and len(data["profiles"]) > 0:
                raw_list = data["profiles"]
            elif "accounts" in data and isinstance(data["accounts"], list) and len(data["accounts"]) > 0:
                raw_list = data["accounts"]
            elif isinstance(data, list) and len(data) > 0:
                raw_list = data
            elif isinstance(data, dict):
                raw_list = [data]

            profiles = [
                AvantureCredentialsStore.normalize_profile(x, idx=i) 
                for i, x in enumerate(raw_list)
            ]
            if not profiles:
                profiles = [dict(def_prof)]

            first = profiles[0]
            return profiles, first.get("proxy", DEFAULT_PROXY_URL), first.get("image_path", "")
        except Exception:
            return [dict(def_prof)], def_prof["proxy"], ""

    @staticmethod
    def clear():
        try:
            if AVANTURE_CREDS_FILE.exists():
                AVANTURE_CREDS_FILE.unlink()
        except Exception:
            pass


