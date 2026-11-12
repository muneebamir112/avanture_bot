import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from playwright.sync_api import sync_playwright

from config import DATA_DIR, SESSION_FILE

TARGET_URL = "https://www.avanture.net/classifieds/edit"
OUTPUT_JSON = DATA_DIR / "dropdowns.json"
OUTPUT_EXCEL = DATA_DIR / "dropdowns.xlsx"

def scrape_dropdowns():
    print(f"\n=======================================================")
    print(f" Avanture Classifieds Dropdown Scraper")
    print(f" Target: {TARGET_URL}")
    print(f"=======================================================\n")
    print("Launching visible browser window...")

    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        context_kwargs = {
            "no_viewport": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        if SESSION_FILE.exists() and SESSION_FILE.stat().st_size > 10:
            print(f"Loading existing session from {SESSION_FILE.name}...")
            context_kwargs["storage_state"] = str(SESSION_FILE)

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        print(f"Opening {TARGET_URL}...")
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            print(f"Initial navigation: {e}")

        # Check if Cloudflare or Login screen is active
        print("\nChecking page status...")
        while True:
            title = page.title()
            current_url = page.url

            if "Attention Required" in title or "Cloudflare" in title or "Just a moment" in title:
                print(">> Cloudflare verification challenge detected on screen.")
                print(">> Please complete the verification in the open browser window...")
                time.sleep(3)
            elif "login" in current_url.lower() or "signin" in current_url.lower():
                print(">> Login required. Please log in to your Avanture account in the browser...")
                time.sleep(3)
            else:
                # We have reached a non-cloudflare, non-login page or the form
                # Let's check if form elements or selects exist
                page.wait_for_timeout(2000)
                select_count = page.locator("select").count()
                custom_dropdowns = page.locator("[role='combobox'], [role='listbox'], .select, .dropdown, select").count()
                
                if select_count > 0 or custom_dropdowns > 0 or "classifieds" in current_url.lower():
                    print(f"\nTarget form loaded! Found {select_count} standard <select> elements.")
                    break
                else:
                    print(f"Current page: '{title}' ({current_url}). Waiting for classifieds edit form to load...")
                    time.sleep(3)

        # Save session so we don't have to verify every time
        try:
            context.storage_state(path=str(SESSION_FILE))
            print(f"Session state saved to {SESSION_FILE.name}")
        except Exception as e:
            print(f"Notice: Could not save session state: {e}")

        # Wait a moment for dynamic options / AJAX to populate
        page.wait_for_timeout(2500)

        # Scrape all <select> elements
        print("\nExtracting dropdown elements and options...")
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")

        selects = soup.find_all("select")
        print(f"Total <select> elements detected in DOM: {len(selects)}")

        dropdown_data = {}
        flat_records = []

        for idx, sel in enumerate(selects):
            sel_id = sel.get("id", f"select_{idx}")
            sel_name = sel.get("name", f"select_{idx}")
            
            # Find associated label if any
            label_text = ""
            if sel.get("id"):
                lbl = soup.find("label", attrs={"for": sel["id"]})
                if lbl:
                    label_text = lbl.get_text(strip=True)
            
            if not label_text and sel.parent:
                lbl = sel.parent.find("label")
                if lbl:
                    label_text = lbl.get_text(strip=True)

            identifier = label_text or sel_name or sel_id

            options_list = []
            for opt in sel.find_all("option"):
                val = opt.get("value", "")
                text = opt.get_text(strip=True)
                is_selected = opt.has_attr("selected")
                
                options_list.append({
                    "value": val,
                    "text": text,
                    "selected": is_selected
                })

                flat_records.append({
                    "Dropdown ID": sel_id,
                    "Dropdown Name": sel_name,
                    "Label": label_text,
                    "Option Value": val,
                    "Option Text": text,
                    "Default Selected": is_selected
                })

            dropdown_data[sel_name or sel_id] = {
                "id": sel_id,
                "name": sel_name,
                "label": label_text,
                "total_options": len(options_list),
                "options": options_list
            }

        # Also inspect custom comboboxes or dropdown-like widgets (Bootstrap, Select2, React, etc.)
        custom_widgets = soup.find_all(attrs={"role": ["combobox", "listbox"]})
        custom_dropdown_data = []
        for c_idx, cw in enumerate(custom_widgets):
            custom_dropdown_data.append({
                "tag": cw.name,
                "id": cw.get("id", ""),
                "class": " ".join(cw.get("class", [])),
                "aria_label": cw.get("aria-label", ""),
                "text": cw.get_text(strip=True)[:100]
            })

        output = {
            "source_url": page.url,
            "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_selects": len(dropdown_data),
            "dropdowns": dropdown_data,
            "custom_widgets": custom_dropdown_data
        }

        # Write to JSON
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Saved structured dropdown data to: {OUTPUT_JSON}")

        # Write to Excel
        if flat_records:
            df = pd.DataFrame(flat_records)
            df.to_excel(OUTPUT_EXCEL, index=False)
            print(f"[OK] Saved tabular options spreadsheet to: {OUTPUT_EXCEL}")

        print("\nSummary of Extracted Dropdowns:")
        for name, item in dropdown_data.items():
            lbl = f" ({item['label']})" if item['label'] else ""
            print(f" - {name}{lbl}: {item['total_options']} options")
            # Show top 5 options as preview
            sample_opts = [o['text'] for o in item['options'][:5] if o['text']]
            if sample_opts:
                print(f"     Preview: {', '.join(sample_opts)} ...")

        browser.close()
        print("\nExtraction complete! Browser closed.")

if __name__ == "__main__":
    scrape_dropdowns()

