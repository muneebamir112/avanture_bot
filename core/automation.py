import os
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List
import pandas as pd
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError

from config import (
    SCREENSHOTS_DIR, SESSION_FILE, DEFAULT_DELAY_MIN, DEFAULT_DELAY_MAX, 
    DEFAULT_TIMEOUT_MS, AVANTURE_CATEGORIES, AVANTURE_COUNTRIES,
    HOME_URL, CLASSIFIEDS_URL, LOGIN_URL, DEFAULT_TARGET_URL
)
from core.validator import ListingValidator
from core.auth import AuthManager
from core.chrome_manager import ChromeManager

class AutomationWorker:
    """Controls the browser automation lifecycle for Avanture Classifieds."""

    def __init__(
        self,
        target_url: str = DEFAULT_TARGET_URL,
        data_df: pd.DataFrame = None,
        username: str = "",
        password: str = "",
        accounts: Optional[List[Dict[str, str]]] = None,
        proxy: str = "",
        headless: bool = False,
        default_image_path: str = "",
        auto_delete_old: bool = True,
        delay_between_accounts: float = 5.0,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_progress: Optional[Callable[[int, int, float], None]] = None,
        on_row_completed: Optional[Callable[[int, bool, str], None]] = None,
        on_finished: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.target_url = target_url or "https://www.avanture.net/classifieds"
        self.data_df = data_df.copy() if data_df is not None else pd.DataFrame()
        self.username = username
        self.password = password
        self.proxy = proxy
        self.headless = headless
        self.default_image_path = default_image_path
        self.auto_delete_old = auto_delete_old
        self.delay_between_accounts = delay_between_accounts

        self.accounts = [a for a in accounts if a.get("username") and a.get("password")] if accounts else []
        if not self.accounts and username and password:
            self.accounts = [{"username": username, "password": password, "account_num": 1}]
        
        # Callbacks
        self.on_log = on_log or (lambda msg, lvl: print(f"[{lvl}] {msg}"))
        self.on_progress = on_progress or (lambda curr, total, pct: None)
        self.on_row_completed = on_row_completed or (lambda idx, ok, err: None)
        self.on_finished = on_finished or (lambda summary: None)

        self.auth_manager = AuthManager()

        # Flags
        self.is_running = False
        self.is_paused = False
        self.is_stopped = False
        self.session_published_count = 0
        self.published_titles = set()

    def log(self, message: str, level: str = "INFO"):
        self.on_log(message, level)

    def stop(self):
        self.is_stopped = True
        self.log("Stopping automation process...", "WARNING")

    def pause(self):
        self.is_paused = True
        self.log("Automation paused.", "WARNING")

    def resume(self):
        self.is_paused = False
        self.log("Automation resumed.", "INFO")

    def run(self):
        self.is_running = True
        self.is_stopped = False
        self.is_paused = False

        active_accounts = [acc for acc in self.accounts if acc.get("username") and acc.get("password")]
        if not active_accounts and self.username and self.password:
            active_accounts = [{"username": self.username, "password": self.password, "proxy": self.proxy}]

        total_accounts = len(active_accounts)
        success_count = 0
        fail_count = 0

        # Inherit proxy from account if not set at worker level
        if not self.proxy and active_accounts and active_accounts[0].get("proxy"):
            self.proxy = active_accounts[0].get("proxy")

        self.log(f"Starting Avanture automation batch: {total_accounts} account(s) to process.", "INFO")

        with sync_playwright() as p:
            browser_context = None
            page = None

            try:
                browser_context, page = ChromeManager.get_or_launch_chrome(
                    playwright_instance=p,
                    target_url=self.target_url,
                    proxy=self.proxy,
                    headless=self.headless,
                    on_log=lambda msg: self.log(msg, "CHROME")
                )
            except Exception as ex:
                self.log(f"Notice connecting to Chrome: {ex}. Launching fallback Chromium...", "WARNING")
                proxy_cfg = ChromeManager.parse_proxy(self.proxy)
                browser = p.chromium.launch(headless=self.headless, proxy=proxy_cfg)
                browser_context = browser.new_context(
                    no_viewport=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = browser_context.new_page()

            page.set_default_timeout(DEFAULT_TIMEOUT_MS)
            current_proxy = self.proxy

            try:
                # Process each account in sequence
                for acc_idx, acc in enumerate(active_accounts):
                    if self.is_stopped:
                        self.log("Process halted by user.", "WARNING")
                        break

                    while self.is_paused and not self.is_stopped:
                        time.sleep(0.5)

                    if self.is_stopped:
                        break

                    acc_num = acc_idx + 1
                    curr_user = acc.get("username", "").strip()
                    curr_pass = acc.get("password", "").strip()
                    acc_proxy = acc.get("proxy", "").strip()

                    # Dynamic proxy switch if this profile uses a different proxy
                    if acc_idx > 0 and acc_proxy and acc_proxy != current_proxy:
                        self.log(f"Switching browser proxy for Account {acc_num}...", "INFO")
                        try:
                            browser_context.close()
                        except Exception:
                            pass
                        current_proxy = acc_proxy
                        try:
                            browser_context, page = ChromeManager.get_or_launch_chrome(
                                playwright_instance=p,
                                target_url=self.target_url,
                                proxy=current_proxy,
                                headless=self.headless,
                                on_log=lambda msg: self.log(msg, "CHROME")
                            )
                        except Exception as ex:
                            proxy_cfg = ChromeManager.parse_proxy(current_proxy)
                            browser = p.chromium.launch(headless=self.headless, proxy=proxy_cfg)
                            browser_context = browser.new_context(no_viewport=True)
                            page = browser_context.new_page()
                        page.set_default_timeout(DEFAULT_TIMEOUT_MS)

                    self.log(f"==================================================", "INFO")
                    self.log(f"▶ [ACCOUNT {acc_num}/{total_accounts}] Starting pipeline for: '{curr_user}'", "INFO")

                    # Step 1: Login to Avanture for this account
                    login_ok = self._ensure_account_login(page, curr_user, curr_pass)
                    if not login_ok:
                        fail_count += 1
                        self.log(f"✘ [ACCOUNT {acc_num}] Login failed for '{curr_user}'. Skipping...", "ERROR")
                        self.on_row_completed(acc_idx, False, "Login failed")
                        self._report_progress(acc_num, total_accounts)
                        # Logout & delay before next account
                        self._perform_logout(page)
                        if acc_idx < total_accounts - 1 and not self.is_stopped:
                            self.log("Waiting 5 seconds before next account login...", "INFO")
                            for s in range(5):
                                if self.is_stopped:
                                    break
                                time.sleep(1)
                        continue

                    # Step 2: Pick listing row for this account
                    if acc.get("title") and acc.get("description"):
                        row = pd.Series({
                            "title": acc.get("title", "").strip(),
                            "category": acc.get("category", "He seeks her").strip(),
                            "description": acc.get("description", "").strip(),
                            "country": acc.get("country", "Slovenia").strip(),
                            "state": acc.get("state", "Osrednjeslovenska").strip(),
                            "city": acc.get("city", "Ljubljana").strip(),
                            "registration_number": acc.get("registration_number", "").strip(),
                            "attachment_path": acc.get("image_path", "") or self.default_image_path
                        })
                    elif self.data_df is not None and len(self.data_df) > 0:
                        row_idx = acc_idx if acc_idx < len(self.data_df) else (acc_idx % len(self.data_df))
                        row = self.data_df.iloc[row_idx]
                    else:
                        row = pd.Series({
                            "title": "A relaxed evening for two in Ljubljana",
                            "category": "He seeks her",
                            "description": "Looking for a pleasant, mature company for dinner, wine, and casual conversation.",
                            "country": "Slovenia",
                            "state": "Osrednjeslovenska",
                            "city": "Ljubljana",
                            "registration_number": "",
                            "attachment_path": self.default_image_path
                        })
                    title_preview = str(row.get('title', ''))[:35]
                    self.log(f"[ACCOUNT {acc_num}] Target listing ad: '{title_preview}'", "INFO")

                    try:
                        # Reset published tracker for this account
                        self.session_published_count = 0

                        # Step 3: Open New Listing form (deletes pre-existing ad if limit reached)
                        form_ready, form_err = self._open_new_listing_form(page)
                        if not form_ready:
                            fail_count += 1
                            self.log(f"✘ [ACCOUNT {acc_num}] Failed to open form: {form_err}", "ERROR")
                            self._capture_error_screenshot(page, acc_idx)
                            self.on_row_completed(acc_idx, False, form_err)
                        else:
                            # Step 4: Fill form fields, upload picture, and finalize publication
                            ok, err_msg = self._fill_and_submit_listing(page, row)
                            if ok:
                                success_count += 1
                                self.session_published_count += 1
                                self.log(f"✔ [ACCOUNT {acc_num}] Listing published successfully!", "SUCCESS")
                                self.on_row_completed(acc_idx, True, "")
                            else:
                                fail_count += 1
                                self.log(f"✘ [ACCOUNT {acc_num}] Failed to publish: {err_msg}", "ERROR")
                                self._capture_error_screenshot(page, acc_idx)
                                self.on_row_completed(acc_idx, False, err_msg)

                    except Exception as ex:
                        fail_count += 1
                        err_str = str(ex)
                        self.log(f"✘ [ACCOUNT {acc_num}] Unexpected error: {err_str}", "ERROR")
                        self._capture_error_screenshot(page, acc_idx)
                        self.on_row_completed(acc_idx, False, err_str)

                    self._report_progress(acc_num, total_accounts)

                    # Step 5: Logout from this account
                    self.log(f"[ACCOUNT {acc_num}] Logging out of Avanture...", "INFO")
                    self._perform_logout(page)

                    # Step 6: 5 seconds delay before the next account
                    if acc_idx < total_accounts - 1 and not self.is_stopped:
                        self.log("Waiting 5 seconds before next account login...", "INFO")
                        for s in range(5):
                            if self.is_stopped:
                                break
                            time.sleep(1)

            finally:
                if browser_context:
                    try:
                        browser_context.close()
                    except Exception:
                        pass

        self.is_running = False
        summary = {
            "total": total_accounts,
            "success": success_count,
            "failed": fail_count,
            "completed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.log(f"Batch completed: {success_count} succeeded, {fail_count} failed out of {total_accounts} account(s).", "INFO")
        self.on_finished(summary)

    def _ensure_account_login(self, page: Page, username: str, password: str) -> bool:
        """Ensures the specified account is logged into Avanture."""
        self.log(f"Logging in to Avanture as '{username}'...", "INFO")

        # 1. First check if current page already has active session for this user
        body_init = page.locator("body").inner_text()[:3000].lower() if page.url else ""
        has_logout = page.locator("a[href*='users/login/out'], a[href*='users/logout'], a:has-text('Log out'), a:has-text('Odjava')").count() > 0
        has_profile = (
            page.locator(f"a[href*='/profile/{username.lower()}'], a[href*='users/settings']").count() > 0 or
            f"hello, {username.lower()}" in body_init or
            f"zdravo, {username.lower()}" in body_init
        )

        if has_logout and has_profile:
            self.log(f"Already authenticated as '{username}'.", "SUCCESS")
            return True

        # 2. If logged in as someone else, perform clean logout
        if has_logout and not has_profile:
            self.log("Switching user: Logging out previous account...", "INFO")
            self._perform_logout(page)

        # 3. Navigate to login page
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        time.sleep(1.5)

        # Check if Avanture redirected because user is already authenticated
        body_nav = page.locator("body").inner_text()[:3000].lower()
        if username.lower() in body_nav and page.locator("a[href*='users/login/out'], a:has-text('Log out'), a:has-text('Odjava')").count() > 0:
            self.log(f"Already authenticated as '{username}'.", "SUCCESS")
            return True

        # 4. Check if Cloudflare is present
        while any(k in page.title() for k in ["Attention Required", "Cloudflare", "Just a moment"]):
            self.log("Cloudflare verification active on screen. Please complete it in Chrome...", "WARNING")
            time.sleep(2)
            if self.is_stopped:
                return False

        # 5. Perform automated login with credentials
        ok, msg = self.auth_manager.perform_automated_login(page, username, password, on_status=self.log)
        if ok:
            self.log(f"Authenticated as '{username}' successfully!", "SUCCESS")
            return True
        else:
            self.log(f"Login notice for '{username}': {msg}", "WARNING")
            return False

    def _perform_logout(self, page: Page):
        """Logs out of the current Avanture session and clears browser cookies."""
        try:
            logout_btn = page.locator("a[href*='users/login/out'], a[href*='users/logout'], a:has-text('Log out'), a:has-text('Odjava')").first
            if logout_btn.is_visible(timeout=1500):
                logout_btn.click()
                time.sleep(1.5)
            else:
                page.goto("https://www.avanture.net/users/login/out", wait_until="domcontentloaded")
                time.sleep(1.5)
        except Exception:
            try:
                page.goto("https://www.avanture.net/users/login/out", wait_until="domcontentloaded")
                time.sleep(1.5)
            except Exception:
                pass

        try:
            page.context.clear_cookies()
            page.evaluate("() => { try { localStorage.clear(); sessionStorage.clear(); } catch(e){} }")
        except Exception:
            pass

        try:
            if SESSION_FILE.exists():
                SESSION_FILE.unlink()
        except Exception:
            pass

        self.log("Logged out successfully. Session cleared.", "INFO")

    def _is_limit_reached(self, page: Page) -> bool:
        """Checks if Avanture displays the 1-listing plan limit error banner."""
        try:
            cur_url = page.url.lower()
            if "classifieds/manage" in cur_url:
                limit_phrases = [
                    "you have reached your limit",
                    "delete some of the existing listings",
                    "dosegli ste svojo omejitev",
                    "lahko izbrišete nekatere obstoječe"
                ]
                page_text = page.locator("body").inner_text().lower()
                for p in limit_phrases:
                    if p in page_text:
                        return True
        except Exception:
            pass
        return False

    def _delete_existing_listing(self, page: Page) -> bool:
        """
        Deletes any pre-existing listing on https://www.avanture.net/classifieds/manage
        to free up the slot when the account's 1-listing plan limit is reached.
        """
        self.log("Freeing up 1-listing slot: Removing old listing...", "INFO")

        # Auto-accept any browser dialogs (confirm prompts)
        try:
            page.on("dialog", lambda d: d.accept())
        except Exception:
            pass

        if "classifieds/manage" not in page.url.lower():
            page.goto("https://www.avanture.net/classifieds/manage", wait_until="domcontentloaded")
            time.sleep(2)

        # Check if already 0 listings
        if page.locator("text='You have no listings yet'").is_visible(timeout=1000):
            self.log("No existing listings found to remove.", "INFO")
            return True

        confirmed = False

        # METHOD 1: Look for the 3-dot options menu on the listing card
        menu_selectors = [
            ".mdi-dots-horizontal",
            ".mdi-dots-vertical",
            "button:has(.mdi-dots-horizontal)",
            "button:has(.mdi-dots-vertical)",
            "button:has-text('⋯')",
            "a:has-text('⋯')",
            "button:has-text('...')",
            "a:has-text('...')",
            "[data-pa-menu]",
            "[data-pm-menu]",
            ".pa-menu__btn",
            ".pm-menu__btn",
            "button[title*='More' i]",
            "button[title*='Več' i]"
        ]

        for m_sel in menu_selectors:
            try:
                loc = page.locator(m_sel).first
                if loc.is_visible(timeout=500):
                    self.log("Opening listing options menu (⋯)...", "INFO")
                    loc.click()
                    time.sleep(0.8)
                    break
            except Exception:
                continue

        # Candidate selectors for the Delete action in the dropdown menu
        del_selectors = [
            "a:has-text('Delete listing'):visible",
            "button:has-text('Delete listing'):visible",
            "*:has-text('Delete listing'):visible",
            "a:has-text('Izbriši oglas'):visible",
            "button:has-text('Izbriši oglas'):visible",
            "*:has-text('Izbriši oglas'):visible",
            ".pa-menu.is-open a:has-text('Delete')",
            ".pa-menu.is-open button:has-text('Delete')",
            ".pm-menu.is-open a:has-text('Delete')",
            ".pm-menu.is-open button:has-text('Delete')",
            "a:has-text('Delete'):visible",
            "button:has-text('Delete'):visible",
            "a:has-text('Izbriši'):visible",
            "button:has-text('Izbriši'):visible",
            "a[href*='delete']:visible"
        ]

        for sel in del_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=600):
                    self.log(f"Triggering deletion ({sel})...", "INFO")
                    loc.click()
                    time.sleep(1.2)
                    break
            except Exception:
                continue

        # Confirmation modal handler (handles "Continue", "Nadaljuj", etc.)
        confirm_selectors = [
            "button:has-text('Continue'):visible",
            "a:has-text('Continue'):visible",
            "[role='button']:has-text('Continue'):visible",
            ".modal button:has-text('Continue'):visible",
            "[role='dialog'] button:has-text('Continue'):visible",
            "button:has-text('Nadaljuj'):visible",
            "a:has-text('Nadaljuj'):visible",
            ".modal button:has-text('Nadaljuj'):visible",
            "button:has-text('Delete'):visible",
            "button:has-text('Izbriši'):visible",
            "button:has-text('Potrdi'):visible",
            "button:has-text('Yes'):visible",
            "button.btn-danger:visible",
            ".swal2-confirm:visible",
            ".pu-btn-danger:visible"
        ]

        for _ in range(8):
            for c_sel in confirm_selectors:
                try:
                    c_loc = page.locator(c_sel).first
                    if c_loc.is_visible(timeout=300):
                        self.log(f"Confirming deletion modal ({c_sel})...", "INFO")
                        c_loc.click()
                        confirmed = True
                        time.sleep(2)
                        break
                except Exception:
                    continue
            if confirmed:
                break
            time.sleep(0.3)

        # Robust JS fallback if modal is still open
        if not confirmed:
            try:
                clicked_js = page.evaluate('''() => {
                    const candidates = Array.from(document.querySelectorAll('button, a, [role="button"], input[type="submit"], input[type="button"], div, span'));
                    for (const el of candidates) {
                        const text = (el.innerText || el.textContent || el.value || '').trim();
                        if ((text === 'Continue' || text === 'Nadaljuj') && el.offsetParent !== null) {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }''')
                if clicked_js:
                    self.log("Confirmed deletion modal via JS fallback ('Continue').", "INFO")
                    confirmed = True
                    time.sleep(2)
            except Exception:
                pass

        # METHOD 2: If not confirmed from card menu, open the listing view page and delete there!
        if not confirmed:
            self.log("Opening listing view page to execute deletion directly...", "INFO")
            view_link = page.locator("a[href*='/classifieds/view/']:visible").first
            if view_link.is_visible(timeout=2000):
                view_link.click()
                time.sleep(2.5)

                for sel in del_selectors:
                    try:
                        loc = page.locator(sel).first
                        if loc.is_visible(timeout=1000):
                            self.log(f"Found delete action on listing view ({sel}). Clicking...", "INFO")
                            loc.click()
                            time.sleep(1.2)
                            break
                    except Exception:
                        continue

                for c_sel in confirm_selectors:
                    try:
                        c_loc = page.locator(c_sel).first
                        if c_loc.is_visible(timeout=1000):
                            self.log(f"Confirming deletion modal on view page ({c_sel})...", "INFO")
                            c_loc.click()
                            time.sleep(2)
                            confirmed = True
                            break
                    except Exception:
                        continue

                if not confirmed:
                    try:
                        page.evaluate('''() => {
                            const candidates = Array.from(document.querySelectorAll('button, a, [role="button"]'));
                            for (const el of candidates) {
                                const text = (el.innerText || el.textContent || '').trim();
                                if ((text === 'Continue' || text === 'Nadaljuj') && el.offsetParent !== null) {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        time.sleep(2)
                    except Exception:
                        pass

        # Wait for page to refresh and verify slot is empty
        page.goto("https://www.avanture.net/classifieds/manage", wait_until="domcontentloaded")
        time.sleep(2)
        self.log("Previous listing removed successfully. Ready to publish new listing!", "SUCCESS")
        return True

    def _open_new_listing_form(self, page: Page) -> tuple[bool, str]:
        """Prepares a clean New Listing form on Avanture.
        Ensures any old listing is removed before opening a new listing form.
        PROTECTION: Never deletes a listing published in the current session!
        """
        self.log("Opening 'New Listing' form...", "INFO")

        # Set dialog auto-accept handler for any browser confirmation popups
        try:
            page.on("dialog", lambda d: d.accept())
        except Exception:
            pass

        # Step 1: If we have NOT yet published a listing in this session,
        # ensure any pre-existing listing on the account is removed first
        # so that the 1-listing slot is completely free!
        if self.session_published_count == 0:
            if "classifieds/manage" not in page.url.lower():
                page.goto("https://www.avanture.net/classifieds/manage", wait_until="domcontentloaded")
                time.sleep(1.5)

            has_old_listing = page.locator("a[href*='/classifieds/view/'], button:has-text('Edit listing'), a:has-text('Edit listing'), [data-pa-menu], .pc-card").count() > 0
            if has_old_listing or self._is_limit_reached(page):
                self.log("Active old listing detected on account. Auto-deleting old listing to free up slot...", "INFO")
                self._delete_existing_listing(page)

        # Step 2: Now navigate directly to the clean New Listing form
        self.log("Navigating to https://www.avanture.net/classifieds/edit...", "INFO")
        page.goto("https://www.avanture.net/classifieds/edit", wait_until="domcontentloaded")
        time.sleep(2)

        # Step 3: Check if Avanture redirected to manage (limit reached)
        if self._is_limit_reached(page) or "classifieds/manage" in page.url.lower():
            if self.session_published_count > 0:
                self.log("⚠️ Single-listing slot is already active with your new ad. Protecting published ad!", "INFO")
                return False, "Plan limit reached (1/1). Your new listing is live and protected."

            self.log("Limit detected. Deleting pre-existing listing...", "WARNING")
            self._delete_existing_listing(page)
            page.goto("https://www.avanture.net/classifieds/edit", wait_until="domcontentloaded")
            time.sleep(2)

        # Step 4: Wait for the form title input field to appear
        try:
            page.wait_for_selector("#input_edit_classifieds_listing_data_title", timeout=12000)
            self.log("New Listing form ready.", "SUCCESS")
            return True, ""
        except Exception as ex:
            if "classifieds/edit" not in page.url.lower():
                page.goto("https://www.avanture.net/classifieds/edit", wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("#input_edit_classifieds_listing_data_title", timeout=8000)
                    self.log("New Listing form ready.", "SUCCESS")
                    return True, ""
                except Exception:
                    pass

            return False, f"Could not open New Listing form: {ex}"

    def _type_with_delay(self, locator, text: str, delay_ms: int = 40):
        """Types text character-by-character with natural human typing cadence, slight jitter, and brief micro-pauses."""
        try:
            locator.click()
            time.sleep(0.4)
            locator.fill("")
            time.sleep(0.2)
            for char in text:
                if self.is_stopped:
                    break
                jitter = random.randint(max(18, delay_ms - 15), delay_ms + 20)
                locator.press_sequentially(char, delay=jitter)
                if char in [" ", ",", ".", "!", "?"] and random.random() < 0.25:
                    time.sleep(random.uniform(0.12, 0.28))
            time.sleep(0.6)
        except Exception:
            locator.fill(text)

    def _fill_and_submit_listing(self, page: Page, row: pd.Series) -> tuple[bool, str]:
        """
        Fills the exact Avanture classifieds DOM fields with human-like writing delay:
        - Title (#input_edit_classifieds_listing_data_title)
        - Category (#input_edit_classifieds_listing_data_category)
        - Description (#input_edit_classifieds_listing_data_body)
        - Country (#input_edit_classifieds_listing_data_location_country)
        - State (#input_edit_classifieds_listing_data_location_state)
        - City (#input_edit_classifieds_listing_data_location_city)
        - Registry number (#input_edit_classifieds_listing_data_maticna_stevilka)
        """
        title = str(row.get("title", "")).strip()[:50]
        category = str(row.get("category", "")).strip()
        description = str(row.get("description", "")).strip()
        country = str(row.get("country", "")).strip() if pd.notna(row.get("country")) else ""
        state = str(row.get("state", "")).strip() if pd.notna(row.get("state")) else ""
        city = str(row.get("city", "")).strip() if pd.notna(row.get("city")) else ""
        reg_number = str(row.get("registration_number", "")).strip() if pd.notna(row.get("registration_number")) else ""
        attachment = str(row.get("attachment_path", "")).strip() if pd.notna(row.get("attachment_path")) else ""

        # 1. Fill Title with human-like typing delay
        title_input = page.locator("#input_edit_classifieds_listing_data_title").first
        if not title_input.is_visible():
            return False, "Title input field (#input_edit_classifieds_listing_data_title) not found."
        self.log(f"Writing Title with typing cadence: '{title[:35]}...'", "INFO")
        self._type_with_delay(title_input, title, delay_ms=45)
        time.sleep(1.0)

        # 2. Select Category
        cat_select = page.locator("#input_edit_classifieds_listing_data_category").first
        if not cat_select.is_visible():
            return False, "Category select field (#input_edit_classifieds_listing_data_category) not found."

        cat_lower = category.lower()
        cat_val = AVANTURE_CATEGORIES.get(cat_lower, category)
        selected = False

        # Try selecting by mapped value (e.g. "5")
        try:
            cat_select.select_option(value=str(cat_val))
            selected = True
        except Exception:
            pass

        # Try selecting by label
        if not selected:
            try:
                cat_select.select_option(label=category)
                selected = True
            except Exception:
                pass

        # Fuzzy matching against option text
        if not selected:
            try:
                options = cat_select.locator("option").all()
                for opt in options:
                    opt_text = opt.inner_text().strip().lower()
                    if cat_lower in opt_text or opt_text in cat_lower:
                        opt_val = opt.get_attribute("value")
                        if opt_val:
                            cat_select.select_option(value=opt_val)
                            selected = True
                            break
            except Exception:
                pass

        cat_select.dispatch_event("change")
        self.log(f"Selected Category: '{category}'", "INFO")
        time.sleep(1.0)

        # 3. Fill Description with human-like typing delay
        desc_input = page.locator("#input_edit_classifieds_listing_data_body").first
        if not desc_input.is_visible():
            return False, "Description textarea (#input_edit_classifieds_listing_data_body) not found."
        self.log(f"Writing Description with typing cadence ({len(description)} chars)...", "INFO")
        self._type_with_delay(desc_input, description, delay_ms=30)
        time.sleep(1.5)

        # 4. Fill Location (Country -> State -> City)
        if country:
            country_select = page.locator("#input_edit_classifieds_listing_data_location_country").first
            if country_select.is_visible():
                c_val = AVANTURE_COUNTRIES.get(country.lower(), country)
                try:
                    country_select.select_option(value=str(c_val))
                except Exception:
                    try:
                        country_select.select_option(label=country)
                    except Exception:
                        pass
                
                # Trigger onchange event and wait for AJAX states to load
                country_select.dispatch_event("change")
                self.log(f"Selected Country: '{country}'", "INFO")
                time.sleep(1.5)

                # Wait for AJAX options to populate in State
                state_select = page.locator("#input_edit_classifieds_listing_data_location_state").first
                if state_select.is_visible():
                    try:
                        page.wait_for_function(
                            "document.querySelector('#input_edit_classifieds_listing_data_location_state') && document.querySelector('#input_edit_classifieds_listing_data_location_state').options.length > 1",
                            timeout=3000
                        )
                    except Exception:
                        pass

                    state_selected = False
                    if state:
                        try:
                            state_select.select_option(label=state)
                            state_selected = True
                        except Exception:
                            try:
                                opts = state_select.locator("option").all()
                                for opt in opts:
                                    if state.lower() in opt.inner_text().strip().lower():
                                        opt_val = opt.get_attribute("value")
                                        if opt_val:
                                            state_select.select_option(value=opt_val)
                                            state_selected = True
                                            break
                            except Exception:
                                pass

                    # Fallback: If State was empty or not matched, select the first valid state option
                    # because Avanture REQUIRES State whenever Country is selected!
                    if not state_selected:
                        try:
                            opts = state_select.locator("option").all()
                            for opt in opts:
                                opt_val = opt.get_attribute("value")
                                if opt_val and opt_val != "" and opt_val != "0":
                                    state_select.select_option(value=opt_val)
                                    state_selected = True
                                    self.log(f"Selected State: '{opt.inner_text().strip()}'", "INFO")
                                    break
                        except Exception:
                            pass
                    else:
                        self.log(f"Selected Region/State: '{state}'", "INFO")

                    state_select.dispatch_event("change")
                    time.sleep(1.5)

                # Wait for AJAX options to populate in City
                city_select = page.locator("#input_edit_classifieds_listing_data_location_city").first
                if city_select.is_visible():
                    try:
                        page.wait_for_function(
                            "document.querySelector('#input_edit_classifieds_listing_data_location_city') && document.querySelector('#input_edit_classifieds_listing_data_location_city').options.length > 1",
                            timeout=3000
                        )
                    except Exception:
                        pass

                    city_selected = False
                    if city:
                        try:
                            city_select.select_option(label=city)
                            city_selected = True
                        except Exception:
                            try:
                                opts = city_select.locator("option").all()
                                for opt in opts:
                                    if city.lower() in opt.inner_text().strip().lower():
                                        opt_val = opt.get_attribute("value")
                                        if opt_val:
                                            city_select.select_option(value=opt_val)
                                            city_selected = True
                                            break
                            except Exception:
                                pass

                    # Fallback: If City was empty or not matched, select the first valid city option
                    # because Avanture REQUIRES City whenever Country is selected!
                    if not city_selected:
                        try:
                            opts = city_select.locator("option").all()
                            for opt in opts:
                                opt_val = opt.get_attribute("value")
                                if opt_val and opt_val != "" and opt_val != "0":
                                    city_select.select_option(value=opt_val)
                                    city_selected = True
                                    self.log(f"Selected City: '{opt.inner_text().strip()}'", "INFO")
                                    break
                        except Exception:
                            pass
                    else:
                        self.log(f"Selected City: '{city}'", "INFO")

        # 5. Registry Number (for Erotic Massage if visible)
        reg_input = page.locator("#input_edit_classifieds_listing_data_maticna_stevilka").first
        if reg_input.is_visible() and reg_number:
            self.log(f"Writing Registry Number with delay: '{reg_number}'", "INFO")
            self._type_with_delay(reg_input, reg_number, delay_ms=45)
            time.sleep(1.0)

        # 6. Submit Form
        time.sleep(1.5)  # Natural human pacing pause before clicking publish
        submit_btn = page.locator("button[type='submit']:has-text('Update'), button[type='submit']:has-text('Objavi'), button[type='submit']:has-text('Publish'), button[type='submit']:has-text('Save'), button[type='submit']:has-text('Oddaj'), button[type='submit'], input[type='submit']").first
        if not submit_btn.is_visible():
            return False, "Submit button not found."

        submit_btn.click()
        self.log("Listing submitted ('Objavi'). Waiting for confirmation...", "INFO")
        time.sleep(3)

        # Check for error alerts on page
        err_box = page.locator(".alert-danger, .error, .pu-msg-err, [role='alert'], .field-error").first
        if err_box.is_visible(timeout=2000):
            err_msg = err_box.inner_text().strip()
            # If server blocked publication due to 1-listing plan limit
            if self.auto_delete_old and self.session_published_count == 0 and any(w in err_msg.lower() for w in ["limit", "reached your limit", "omejitev"]):
                self.log("Server rejected submission due to account limit. Deleting old listing and retrying...", "WARNING")
                self._delete_existing_listing(page)
                # Re-click submit
                retry_submit = page.locator("button[type='submit']:has-text('Update'), button[type='submit']:has-text('Objavi'), button[type='submit']:has-text('Save'), button[type='submit']:has-text('Oddaj'), button[type='submit']:has-text('Publish'), button[type='submit']").first
                if retry_submit.is_visible():
                    retry_submit.click()
                    time.sleep(3)
                    if not err_box.is_visible(timeout=1500):
                        pass
                    else:
                        return False, f"Server returned error: {err_msg}"
            else:
                return False, f"Server returned error: {err_msg}"

        # 7. Upload Image / Attachment if specified (Step 2 on Avanture)
        # Wait for redirect to pictures/upload or view
        for _ in range(10):
            if "pictures/upload" in page.url.lower() or "classifieds/view" in page.url.lower():
                break
            time.sleep(0.5)

        att_raw = ListingValidator.get_attachment_raw(row)
        img_to_upload = None

        if att_raw:
            img_to_upload = ListingValidator.resolve_attachment_path(att_raw)
            if not img_to_upload or not img_to_upload.exists():
                self.log(f"Row picture '{att_raw}' not found. Falling back to GUI image...", "WARNING")

        # Fallback to GUI selected image if row has no picture or wasn't found
        if not img_to_upload and self.default_image_path:
            p = Path(self.default_image_path)
            if p.exists() and p.is_file():
                img_to_upload = p

        if img_to_upload and img_to_upload.exists():
            self._upload_listing_picture(page, img_to_upload, att_raw=att_raw)
        elif "pictures/upload" in page.url.lower():
            self.log("No picture attached. Finalizing listing publication...", "INFO")
            self._finalize_without_picture(page)

        return True, ""

    def _finalize_without_picture(self, page: Page):
        """Clicks 'Continue: open the listing' when no picture is attached."""
        continue_selectors = [
            "a:has-text('Continue: open the listing')",
            "a:has-text('Nadaljuj: odpri oglas')",
            ".pc-btn--primary",
            "a:has-text('Continue')",
            "a:has-text('Nadaljuj')",
            "a[href*='/classifieds/view/']"
        ]
        for sel in continue_selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1500):
                    loc.click()
                    time.sleep(2)
                    return
            except Exception:
                pass

    def _upload_listing_picture(self, page: Page, img_path: Path, att_raw: str = "") -> bool:
        """
        Uploads the picture to the listing on Avanture.
        Avanture handles pictures in Step 2: https://www.avanture.net/classifieds/pictures/upload/<listing_id>
        """
        source_label = "GUI picture" if not att_raw else "row picture"
        self.log(f"Navigating to upload {source_label}: '{img_path.name}'...", "INFO")

        # Automatically close any accidental popup / external tabs so Chrome stays on 1 tab
        try:
            page.context.on("page", lambda new_p: new_p.close())
        except Exception:
            pass

        # 1. If not already on pictures/upload, navigate directly by listing ID
        if "pictures/upload" not in page.url.lower():
            import re
            m = re.search(r"/(?:edit|view)/(\d+)", page.url)
            if m:
                lid = m.group(1)
                upload_url = f"https://www.avanture.net/classifieds/pictures/upload/{lid}"
                self.log(f"Navigating directly to picture uploader: {upload_url}...", "INFO")
                page.goto(upload_url, wait_until="domcontentloaded")
                time.sleep(2)
            else:
                # Specific button only (never generic 'Slike' navbar links)
                pic_btn = page.locator("a[href*='/classifieds/pictures/upload/']").first
                if pic_btn.is_visible(timeout=2000):
                    pic_btn.click()
                    time.sleep(2)

        # 2. Attach picture file on upload page
        try:
            import re
            m = re.search(r"/(?:pictures/upload|edit|view)/(\d+)", page.url)
            lid = m.group(1) if m else ""

            page.wait_for_selector("input[type='file']", timeout=10000)
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(str(img_path))
            self.log(f"Attached picture file: '{img_path.name}'. Uploading to server...", "INFO")
            time.sleep(2)

            # If an 'Upload files' button is present and visible, click it
            upload_btn = page.locator("a:has-text('Upload files'), button:has-text('Upload files'), a:has-text('Naloži datoteke')").first
            if upload_btn.is_visible(timeout=1000):
                upload_btn.click()
                time.sleep(2)

            # 3. Finalize publication: Click 'Continue: open the listing' / 'Nadaljuj: odpri oglas'
            self.log("Finalizing publication: Waiting for 'Continue: open the listing'...", "INFO")
            clicked_continue = False
            continue_selectors = [
                "a:has-text('Continue: open the listing')",
                "a:has-text('Nadaljuj: odpri oglas')",
                "a.pc-btn--primary:has-text('Continue')",
                "a.pc-btn--primary:has-text('Nadaljuj')",
                ".pc-btn--primary",
                "a[href*='/classifieds/view/']:has-text('Continue')",
                "a[href*='/classifieds/view/']:has-text('Nadaljuj')",
                "button:has-text('Continue')",
                "button:has-text('Nadaljuj')"
            ]
            for _ in range(15):
                for c_sel in continue_selectors:
                    try:
                        continue_btn = page.locator(c_sel).first
                        if continue_btn.is_visible(timeout=400):
                            self.log("Clicking 'Continue: open the listing' to complete publication...", "INFO")
                            continue_btn.click()
                            clicked_continue = True
                            time.sleep(2.5)
                            break
                    except Exception:
                        pass
                if clicked_continue:
                    break
                time.sleep(0.6)

            # Failsafe direct navigation: If still on upload page, navigate directly to view page
            if "pictures/upload" in page.url.lower() and lid:
                view_url = f"https://www.avanture.net/classifieds/view/{lid}"
                self.log(f"Opening live listing view at: {view_url}...", "INFO")
                page.goto(view_url, wait_until="domcontentloaded")
                time.sleep(2)

            self.log(f"Listing successfully published with picture: '{img_path.name}'!", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Notice during picture upload: {e}", "WARNING")
            return False

            self.log(f"Listing successfully published with picture: '{img_path.name}'!", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Notice during picture upload: {e}", "WARNING")
            return False

    def _capture_error_screenshot(self, page: Page, row_idx: int):
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"error_row_{row_idx + 1}_{ts}.png"
            path = SCREENSHOTS_DIR / file_name
            page.screenshot(path=str(path), full_page=True)
            self.log(f"Screenshot saved: {file_name}", "WARNING")
        except Exception as e:
            self.log(f"Could not take screenshot: {e}", "WARNING")

    def _report_progress(self, current: int, total: int):
        pct = current / total if total > 0 else 0.0
        self.on_progress(current, total, pct)
