import os
import sys
import time
import shutil
import socket
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from playwright.sync_api import BrowserContext, Page

from config import BASE_DIR, CHROME_PATH

# Local Chrome profile directory parent root
PROFILES_ROOT = BASE_DIR / "chrome_profiles"
LOCAL_CHROME_PROFILE = PROFILES_ROOT

class ChromeManager:
    """
    Manages launching real Google Chrome with a fresh dedicated profile folder
    created right where the application / exe runs, with full proxy authentication support.
    """

    @classmethod
    def create_new_profile_dir(cls) -> Path:
        """
        Creates a brand-new, isolated Chrome profile directory for the current run,
        and automatically cleans up stale completed profile folders to keep disk space lean.
        """
        PROFILES_ROOT.mkdir(parents=True, exist_ok=True)

        # Attempt to clean up older run profiles that are unlocked
        for item in PROFILES_ROOT.glob("run_profile_*"):
            if item.is_dir():
                try:
                    shutil.rmtree(item, ignore_errors=True)
                except Exception:
                    pass

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        new_dir = PROFILES_ROOT / f"run_profile_{timestamp}"
        new_dir.mkdir(parents=True, exist_ok=True)
        return new_dir

    @staticmethod
    def get_chrome_executable() -> Optional[str]:
        """Locates Chrome / Chromium executable across Windows, macOS, and Linux."""
        candidates = []
        if sys.platform == "darwin":  # macOS
            candidates = [
                CHROME_PATH,
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                os.path.expanduser("~/Applications/Chromium.app/Contents/MacOS/Chromium"),
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                os.path.expanduser("~/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
            ]
        elif sys.platform == "win32":  # Windows
            candidates = [
                CHROME_PATH,
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe")
            ]
        else:  # Linux
            candidates = [
                CHROME_PATH,
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
                "/usr/bin/chromium",
                "/snap/bin/chromium"
            ]
        for path in candidates:
            if path and Path(path).exists():
                return path
        return None

    @staticmethod
    def parse_proxy(proxy_str: str) -> Optional[Dict[str, str]]:
        """
        Parses proxy strings into Playwright proxy dictionary.
        Supports:
          - http://username:password@host:port
          - socks5://username:password@host:port
          - host:port:username:password
          - host:port
          - http://host:port
        """
        if not proxy_str or not proxy_str.strip():
            return None

        clean = proxy_str.strip()

        # Handle host:port:username:password format
        parts = clean.split(":")
        if len(parts) == 4 and not clean.startswith("http://") and not clean.startswith("socks5://"):
            host, port, user, pwd = parts
            return {
                "server": f"http://{host}:{port}",
                "username": user,
                "password": pwd
            }

        if "://" not in clean:
            clean = "http://" + clean

        try:
            parsed = urllib.parse.urlsplit(clean)
            scheme = parsed.scheme if parsed.scheme in ["http", "socks5", "https"] else "http"
            port_part = f":{parsed.port}" if parsed.port else ""
            server = f"{scheme}://{parsed.hostname}{port_part}"
            res = {"server": server}
            if parsed.username:
                res["username"] = urllib.parse.unquote(parsed.username)
            if parsed.password:
                res["password"] = urllib.parse.unquote(parsed.password)
            return res
        except Exception:
            return {"server": clean}

    @classmethod
    def get_or_launch_chrome(
        cls,
        playwright_instance,
        target_url: str = "https://www.avanture.net/",
        proxy: str = "",
        headless: bool = False,
        on_log: Optional[callable] = None
    ) -> Tuple[BrowserContext, Page]:
        """
        Ensures Chrome is running with the local profile and connects Playwright to it.
        Supports proxy with authentication natively.
        """
        def log(msg):
            if on_log:
                on_log(msg)

        profile_dir = cls.create_new_profile_dir()
        log(f"Opening new dedicated Chrome profile: {profile_dir.name}")

        proxy_cfg = cls.parse_proxy(proxy)
        if proxy_cfg:
            user_part = f" (Auth: {proxy_cfg['username']})" if "username" in proxy_cfg else ""
            log(f"Routing browser via proxy: {proxy_cfg['server']}{user_part}")

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ]

        context = None
        # Attempt 1: Launch real Google Chrome channel with the new profile
        try:
            log(f"Launching Google Chrome with fresh profile: {profile_dir.resolve()}")
            context = playwright_instance.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir.resolve()),
                channel="chrome",
                headless=headless,
                proxy=proxy_cfg,
                args=launch_args
            )
        except Exception as e:
            log(f"Notice launching Chrome channel ({e}). Launching standard Chromium...")
            context = playwright_instance.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir.resolve()),
                headless=headless,
                proxy=proxy_cfg,
                args=launch_args
            )

        page = context.pages[0] if context.pages else context.new_page()

        if target_url:
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            except Exception:
                pass

        return context, page
