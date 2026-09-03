"""
create_golden_profile.py
========================
Run this ONCE on your local Windows machine to create a pre-configured
Chrome profile with the Instant Data Scraper extension already installed
and accepted from the Chrome Web Store.
"""

import os
import re
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN_DIR = os.path.join(os.path.expanduser("~"), "golden_profile")
USER_DATA_DIR = os.path.join(GOLDEN_DIR, "User Data")
EXTENSION_ID = "ofaokhiedipichpaobibbnahnkdoiiah"

def _remove_lock(user_data_dir: str):
    lock = Path(user_data_dir) / "SingletonLock"
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass

def main():
    print("\n" + "=" * 50)
    print("   GOLDEN PROFILE CREATOR  (one-time setup)")
    print("=" * 50)
    print(f"\nTarget location : {GOLDEN_DIR}")

    if os.path.exists(GOLDEN_DIR):
        print(f"[OK] Golden profile already exists at:\n    {GOLDEN_DIR}")
        print("\n    Nothing to do. Delete that folder to recreate it.")
        return

    Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
    _remove_lock(USER_DATA_DIR)

    print("[*] Launching Chrome to install extension from Web Store...")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
            ignore_default_args=["--disable-extensions"],
        )
        page = context.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        
        print("[*] Navigating to Chrome Web Store...")
        page.goto(f"https://chromewebstore.google.com/detail/instant-data-scraper/{EXTENSION_ID}")
        
        print("[*] Waiting for 'Add to Chrome' button...")
        try:
            page.bring_to_front()
            add_btn = page.locator('button', has_text=re.compile("Add to Chrome", re.I)).first
            add_btn.wait_for(state="visible", timeout=15000)
            add_btn.click(timeout=5000)
            print("[OK] Clicked 'Add to Chrome'.")
            
            import platform
            os_name = platform.system()
            time.sleep(1.5)
            
            if os_name == "Windows":
                import ctypes
                ctypes.windll.user32.keybd_event(0x25, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(0x25, 0, 2, 0)
                time.sleep(0.5)
                ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
                print("[OK] Windows: Simulated Left Arrow + Enter to accept native dialog.")
                
        except Exception as e:
            print(f"[!] Could not auto-click 'Add to Chrome': {e}")
            print("    Please click it manually and accept the popup.")
            
        print("\n[*] Waiting for extension to open its welcome page...")
        success_auto = False
        for _ in range(60):
            try:
                current_pages = context.pages
            except Exception:
                break
                
            for p_page in current_pages:
                try:
                    if "chromewebstore" not in p_page.url:
                        choose_all = p_page.get_by_text(re.compile("Choose All", re.I))
                        if choose_all.count() > 0:
                            choose_all.first.click(timeout=5000)
                            print("[OK] Auto-clicked 'Choose All' on extension page!")
                            time.sleep(1)
                            
                            confirm_btn = p_page.get_by_text(re.compile("Confirm & Activate", re.I))
                            if confirm_btn.count() > 0:
                                confirm_btn.first.click(timeout=5000)
                                print("[OK] Auto-clicked 'Confirm & Activate' on extension page!")
                                success_auto = True
                                time.sleep(2)
                                break
                except Exception:
                    pass
            if success_auto:
                break
            time.sleep(1)
            
        if not success_auto:
            while True:
                resp = input("\n[!] Automatic setup failed or timed out. Have you finished setting up manually? Type 'yes' to continue: ").strip().lower()
                if resp == 'yes':
                    break
        else:
            print("[OK] Extension setup completed.")
            
        try:
            context.close()
        except Exception:
            pass

    print(f"\n[OK] Golden profile saved to:\n    {GOLDEN_DIR}")

if __name__ == "__main__":
    main()
