"""
create_golden_profile.py
========================
Run this ONCE on your local Windows machine to create a pre-configured
Chrome profile with the Instant Data Scraper extension already accepted.

After running this script:
  1. A browser window will open.
  2. Click "Accept all and continue" on the extension popup (or it auto-clicks).
  3. The browser closes and saves the profile to:
         C:/Users/<You>/golden_profile

Then upload that folder to your server before running server_pipeline.py.
"""

import os
import re
import sys
import time
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ============================================================
# PATHS
# ============================================================
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
EXT_PATH      = os.path.join(BASE_DIR, 'scraper_core', 'ext_unpacked')
GOLDEN_DIR    = os.path.join(os.path.expanduser("~"), "golden_profile")
USER_DATA_DIR = os.path.join(GOLDEN_DIR, "User Data")

# ============================================================
# HELPERS
# ============================================================

def _remove_lock(user_data_dir: str):
    lock = Path(user_data_dir) / "SingletonLock"
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass


def _try_auto_accept(context) -> bool:
    """
    Poll all open pages for any known Instant Data Scraper acceptance
    patterns and click them automatically.
    Returns True if accepted, False if timed out.
    """
    patterns = [
        re.compile(r"accept\s+all\s+and\s+continue", re.I),
        re.compile(r"accept\s+and\s+continue",        re.I),
        re.compile(r"i\s+agree",                      re.I),
    ]
    choose_all_pat  = re.compile(r"choose\s+all",       re.I)
    confirm_act_pat = re.compile(r"confirm.*activate",  re.I)

    for _ in range(90):      # up to 90 seconds
        try:
            pages = context.pages
        except Exception:
            break

        for page in pages:
            try:
                # Pattern A: single "Accept all and continue" button
                for pat in patterns:
                    btn = page.get_by_text(pat)
                    if btn.count() > 0:
                        btn.first.click(timeout=3000)
                        print("[OK] Auto-clicked 'Accept all and continue'!")
                        time.sleep(2)
                        return True

                # Pattern B: "Choose All" -> "Confirm & Activate"
                ca = page.get_by_text(choose_all_pat)
                if ca.count() > 0:
                    ca.first.click(timeout=3000)
                    time.sleep(1)
                    cf = page.get_by_text(confirm_act_pat)
                    if cf.count() > 0:
                        cf.first.click(timeout=3000)
                        print("[OK] Auto-clicked 'Choose All' + 'Confirm & Activate'!")
                        time.sleep(2)
                        return True
            except Exception:
                pass

        time.sleep(1)

    return False


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n" + "=" * 50)
    print("   GOLDEN PROFILE CREATOR  (one-time setup)")
    print("=" * 50)
    print(f"\nTarget location : {GOLDEN_DIR}")
    print(f"Extension folder: {EXT_PATH}\n")

    # Guard: already exists
    if os.path.exists(GOLDEN_DIR):
        print(f"[OK] Golden profile already exists at:\n    {GOLDEN_DIR}")
        print("\n    Nothing to do. Delete that folder to recreate it.")
        return

    # Guard: extension must be present
    if not os.path.isdir(EXT_PATH):
        print(f"[!] Extension folder not found:\n    {EXT_PATH}")
        print("    Make sure scraper_core/ext_unpacked/ exists.")
        sys.exit(1)

    # Create directory skeleton
    Path(USER_DATA_DIR).mkdir(parents=True, exist_ok=True)
    _remove_lock(USER_DATA_DIR)

    print("[*] Launching Chrome with extension loaded...")
    print("    When the browser opens:")
    print("    -> Click 'Accept all and continue' on the extension popup.")
    print("    -> The script will detect it and close the browser for you.\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            channel="chrome",      # use real Chrome on Windows
            headless=False,
            args=[
                f"--load-extension={EXT_PATH}",
                f"--disable-extensions-except={EXT_PATH}",
                "--disable-dev-shm-usage",
            ],
            viewport=None,
            timeout=30_000,
            ignore_default_args=[
                "--disable-extensions",
                "--disable-component-extensions-with-background-pages",
            ],
        )

        # Try to auto-accept extension T&C
        success = _try_auto_accept(context)

        if not success:
            print("\n[!] Auto-accept timed out or failed.")
            print("    Please click the acceptance button manually in the browser.")
            input("    Then press ENTER here to close the browser: ")

        try:
            context.close()
        except Exception:
            pass

    print(f"\n[OK] Golden profile saved to:\n    {GOLDEN_DIR}")
    print("\nNext steps:")
    print("  1. Zip and upload the 'golden_profile' folder to your server.")
    print("  2. Place it at ~/golden_profile on the server.")
    print("  3. Run: python server_pipeline.py")


if __name__ == "__main__":
    main()
