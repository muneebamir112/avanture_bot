import json
import time
from pathlib import Path
from typing import Optional, Callable, Tuple
from playwright.sync_api import sync_playwright, Page, BrowserContext
from config import SESSION_FILE, LOGIN_URL, DEFAULT_TARGET_URL, HOME_URL
from core.chrome_manager import ChromeManager

class AuthManager:
    """Manages login sessions, credentials, and persistent session state for Avanture."""

    def __init__(self, session_path: Path = SESSION_FILE):
        self.session_path = session_path

    def has_saved_session(self) -> bool:
        """Checks if a saved session file exists and is non-empty."""
        return self.session_path.exists() and self.session_path.stat().st_size > 10

    def clear_session(self):
        """Removes the saved session."""
        if self.session_path.exists():
            self.session_path.unlink()

    def perform_automated_login(
        self,
        page: Page,
        username: str,
        password: str,
        on_status: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        Navigates to the exact Avanture login page (https://www.avanture.net/users/login)
        and fills in credentials using exact DOM element IDs.
        """
        def log(msg: str):
            if on_status:
                on_status(msg)
            else:
                print(msg)

        try:
            # 1. Check if already logged in as this user
            body_init = page.locator("body").inner_text()[:3000].lower() if page.url else ""
            if username.lower() in body_init and (
                page.locator("a[href*='users/login/out'], a[href*='users/logout'], a:has-text('Log out'), a:has-text('Odjava')").count() > 0 or
                f"hello, {username.lower()}" in body_init or
                f"zdravo, {username.lower()}" in body_init
            ):
                log(f"Already authenticated as '{username}'!")
                return True, "Already authenticated"

            # 2. Ensure we are on the Avanture login page
            if "users/login" not in page.url.lower():
                log(f"Opening login page: {LOGIN_URL}...")
                page.goto(LOGIN_URL, wait_until="domcontentloaded")
                time.sleep(1.5)

            # Check again after navigating to login URL (in case Avanture redirects authenticated users)
            body_nav = page.locator("body").inner_text()[:3000].lower()
            if username.lower() in body_nav and (
                page.locator("a[href*='users/login/out'], a[href*='users/logout'], a:has-text('Log out'), a:has-text('Odjava')").count() > 0 or
                f"hello, {username.lower()}" in body_nav or
                f"zdravo, {username.lower()}" in body_nav
            ):
                log(f"Already authenticated as '{username}'!")
                return True, "Already authenticated"

            # 3. Check if Cloudflare is present
            title = page.title()
            if "Attention Required" in title or "Cloudflare" in title or "Just a moment" in title:
                log("Cloudflare 'Verify you are human' screen detected on browser.")
                log(">> Please check the box in the open Chrome browser.")
                
                # Wait until Cloudflare verification is completed by user
                while True:
                    time.sleep(1)
                    cur_title = page.title()
                    if "Attention Required" not in cur_title and "Cloudflare" not in cur_title and "Just a moment" not in cur_title:
                        break
                    # Or if form inputs appear
                    if page.locator("#input_edit_user_login_email, input[name='email']").count() > 0:
                        break

            log("Locating login fields on Avanture...")

            # 4. Wait for Email / Username Input
            user_input = page.locator("#input_edit_user_login_email, input[name='email'], input[name='data_username'], input[name*='user' i]").first
            try:
                user_input.wait_for(state="visible", timeout=10000)
            except Exception:
                # Fallback: check if already logged in
                if page.locator("a[href*='users/login/out'], a:has-text('Log out'), a:has-text('Odjava')").count() > 0:
                    log(f"Already authenticated as '{username}'.")
                    return True, "Already authenticated"
                return False, f"Could not find username/email input field (#input_edit_user_login_email) on {page.url}."

            user_input.click()
            time.sleep(0.3)
            user_input.fill("")
            user_input.press_sequentially(username, delay=35)
            log(f"Typed username/email: {username}")
            time.sleep(0.8)

            # 5. Fill Password
            pass_input = page.locator("#input_edit_user_login_password, input[name='password'], input[type='password']").first
            try:
                pass_input.wait_for(state="visible", timeout=5000)
            except Exception:
                return False, "Could not find password input field (#input_edit_user_login_password)."

            pass_input.click()
            time.sleep(0.3)
            pass_input.fill("")
            pass_input.press_sequentially(password, delay=35)
            log("Typed password.")
            time.sleep(0.8)

            # 6. Check 'Remember me' if present
            remember_chk = page.locator("#input_edit_user_login_remember, input[name='remember']").first
            if remember_chk.is_visible(timeout=1000):
                try:
                    if not remember_chk.is_checked():
                        remember_chk.check()
                except Exception:
                    pass

            # 7. Click Submit Button ('Prijava' / 'Log in')
            submit_btn = page.locator("button[type='submit']:has-text('Prijava'), button[type='submit']:has-text('Log in'), button[type='submit']:has-text('Login'), button[type='submit']").first
            if not submit_btn.is_visible(timeout=2000):
                pass_input.press("Enter")
            else:
                submit_btn.click()

            log("Submitted credentials. Waiting for authentication...")
            page.wait_for_timeout(4000)

            # 8. Check if login was rejected or succeeded
            current_url = page.url.lower()
            if "users/login" in current_url:
                err_loc = page.locator(".alert-danger, .error, .help-block, .pu-msg-err, [role='alert']").first
                if err_loc.is_visible(timeout=1500):
                    err_text = err_loc.inner_text().strip()
                    return False, f"Login failed: {err_text}"
                return False, "Login not completed. Please verify credentials."

            log(f"Login successful! Authenticated on: {page.url}")
            return True, "Login successful"

        except Exception as e:
            return False, f"Automated login error: {str(e)}"

    def test_login(
        self,
        target_url: str = DEFAULT_TARGET_URL,
        username: str = "",
        password: str = "",
        proxy: str = "",
        on_status: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        1. Opens https://www.avanture.net/ first in real Google Chrome.
        2. Checks login state.
        3. If not logged in, clicks Login and automatically submits credentials provided by admin.
        4. Saves session state upon success.
        """
        def log(msg: str):
            if on_status:
                on_status(msg)
            else:
                print(msg)

        start_url = target_url or HOME_URL
        log(f"Connecting to Chrome to open {start_url} first...")
        try:
            with sync_playwright() as p:
                browser, page = ChromeManager.get_or_launch_chrome(
                    playwright_instance=p,
                    target_url=start_url,
                    proxy=proxy,
                    on_log=log
                )
                context = page.context

                # 1. Ensure we are on the homepage first
                log(f"Opening site: {start_url} ...")
                page.goto(start_url, wait_until="domcontentloaded")
                time.sleep(2)

                # Check if Cloudflare is present
                title = page.title()
                if "Attention Required" in title or "Cloudflare" in title or "Just a moment" in title:
                    log("Cloudflare verification active on screen. Please complete it in Chrome...", "WARNING")
                    for _ in range(45):
                        time.sleep(1)
                        if "Attention Required" not in page.title() and "Cloudflare" not in page.title():
                            break

                # 2. Check if already logged in on Avanture
                is_logged_in = page.locator("a[href*='users/logout'], a:has-text('Odjava')").count() > 0
                if is_logged_in:
                    log("Already logged in to Avanture!", "SUCCESS")
                else:
                    # Not logged in yet
                    if username and password:
                        log("Locating Login ('Prijava') on Avanture...")
                        login_link = page.locator("a[href*='users/login'], a:has-text('Login'), a:has-text('Prijava')").first
                        if login_link.is_visible(timeout=3000):
                            login_link.click()
                            time.sleep(1.5)
                        else:
                            page.goto(LOGIN_URL, wait_until="domcontentloaded")
                            time.sleep(1.5)

                        log(f"Logging in with username '{username}'...")
                        ok, msg = self.perform_automated_login(page, username, password, on_status=log)
                        if not ok:
                            log(f"Login notice: {msg}", "WARNING")
                            log("You can complete login manually in the open Chrome window.")
                    else:
                        log("Opening login page. Please log in to your account in the open Chrome window...")
                        page.goto(LOGIN_URL, wait_until="domcontentloaded")

                # 3. Save session state once authenticated
                try:
                    context.storage_state(path=str(self.session_path))
                    log(f"Session state saved to {self.session_path.name}!")
                    return True
                except Exception as ex:
                    log(f"Session save notice: {ex}")
                    return True

        except Exception as e:
            log(f"Login process error: {str(e)}")
            return False

    def launch_manual_login(self, target_url: str, on_status: Optional[Callable[[str], None]] = None) -> bool:
        return self.test_login(target_url=target_url, on_status=on_status)
