import os
import shutil
import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

HEALTHY_PROFILES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'health_profiles.json')
EXTENSION_ID = "ofaokhiedipichpaobibbnahnkdoiiah"
EXTENSION_NAME = "Instant Data Scraper"

def get_base_dir():
    return Path(os.path.expanduser("~"))

def discover_profiles():
    base_dir = get_base_dir()
    # Look for folders starting with ChromeUserData
    profiles = [p for p in base_dir.glob("ChromeUserData*") if p.is_dir()]
    return profiles

def _fetch_manifest(context, ext_id: str):
    page = context.new_page()
    try:
        page.goto(f"chrome-extension://{ext_id}/manifest.json", timeout=5000)
        text = page.evaluate("() => fetch(location.href).then(r => r.text())")
        return json.loads(text)
    except Exception:
        return None
    finally:
        page.close()

def check_extension_installed(user_data_dir: str) -> bool:
    """Headless check to see if the extension loads properly."""
    print(f"Checking health of {Path(user_data_dir).parent.name}...")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=True,
                args=["--headless=new"],
                ignore_default_args=[
                    "--disable-extensions",
                    "--disable-component-extensions-with-background-pages",
                ],
                timeout=15000
            )
            
            try:
                EXTENSION_ID_RE = re.compile(r"chrome-extension://([a-p]+)/")
                candidates = [EXTENSION_ID]
                for sw in context.service_workers:
                    m = EXTENSION_ID_RE.match(sw.url)
                    if m and m.group(1) not in candidates: candidates.append(m.group(1))
                for bg in context.background_pages:
                    m = EXTENSION_ID_RE.match(bg.url)
                    if m and m.group(1) not in candidates: candidates.append(m.group(1))
                
                found = False
                for ext_id in candidates:
                    manifest = _fetch_manifest(context, ext_id)
                    if manifest and EXTENSION_NAME.lower() in manifest.get("name", "").lower():
                        found = True
                        break
                        
                if not found:
                    # Wait for service worker to spawn if not immediately ready
                    try:
                        sw = context.wait_for_event("serviceworker", timeout=5000)
                        m = EXTENSION_ID_RE.match(sw.url)
                        if m:
                            manifest = _fetch_manifest(context, m.group(1))
                            if manifest and EXTENSION_NAME.lower() in manifest.get("name", "").lower():
                                found = True
                    except PWTimeout:
                        pass
                        
                return found
            finally:
                context.close()
    except Exception as e:
        print(f"  [!] Error launching profile: {e}")
        return False

import time
def fix_or_create_profile(profile_path: Path):
    user_data_dir = str(profile_path / "User Data") if not (profile_path / "User Data").exists() and not str(profile_path).endswith("User Data") else str(profile_path)
    if not user_data_dir.endswith("User Data"):
        user_data_dir = str(Path(user_data_dir) / "User Data")

    print(f"\nOpening {profile_path.name} in headed mode...")
    print("Automating extension installation...")
    
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport=None,
                ignore_default_args=["--disable-extensions"],
            )
            page = context.new_page()
            
            # Auto-handle standard dialogs just in case
            page.on("dialog", lambda dialog: dialog.accept())
            
            page.goto(f"https://chromewebstore.google.com/detail/instant-data-scraper/{EXTENSION_ID}")
            
            print("\nWaiting for 'Add to Chrome' button...")
            try:
                # The button in the new CWS
                page.bring_to_front()
                add_btn = page.locator('button', has_text=re.compile("Add to Chrome", re.I)).first
                add_btn.wait_for(state="visible", timeout=15000)
                add_btn.click(timeout=5000)
                print("Clicked 'Add to Chrome'.")
                
                print("\nAutomating native Chrome popup using ctypes...")
                import ctypes
                time.sleep(1.5) # wait for popup to appear
                # Press Left Arrow (VK_LEFT = 0x25)
                ctypes.windll.user32.keybd_event(0x25, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(0x25, 0, 2, 0)
                
                time.sleep(0.5)
                # Press Enter (VK_RETURN = 0x0D)
                ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
                print("Simulated Left Arrow + Enter.")
                
            except Exception as e:
                print(f"Could not auto-click 'Add to Chrome': {e}")
                print("Please click it manually and accept the popup.")
            
            print("\nWaiting for extension to open its welcome page...")
            success_auto = False
            for _ in range(60):
                try:
                    current_pages = context.pages
                except Exception:
                    break
                    
                for p_page in current_pages:
                    try:
                        if "chromewebstore" not in p_page.url:
                            agree_btn = p_page.get_by_role("button", name=re.compile("agree|accept|continue", re.I))
                            if agree_btn.count() > 0:
                                agree_btn.first.click(timeout=5000)
                                print("Auto-clicked 'Agree' on extension page!")
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
                    resp = input("\nAutomatic setup failed or timed out. Have you finished setting up manually? Type 'yes' to continue: ").strip().lower()
                    if resp == 'yes':
                        break
            else:
                print("Extension setup completed. Closing browser...")
            
            try:
                context.close()
            except:
                pass
                
        # --- VERIFICATION STEP ---
        print("\nRe-opening browser for your final verification...")
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=False,
                viewport=None,
                ignore_default_args=["--disable-extensions"],
            )
            v_page = context.new_page()
            v_page.goto("https://www.google.com/maps")
            
            while True:
                resp = input(f"\nPlease verify the extension is working in {profile_path.name}. Type 'yes' to confirm and move forward: ").strip().lower()
                if resp == 'yes':
                    break
            
            try:
                context.close()
            except:
                pass

    except Exception as e:
        print(f"Error during setup: {e}")

    if check_extension_installed(user_data_dir):
        print(f"[✅] Profile {profile_path.name} is now Healthy!")
        return True
    else:
        print(f"[❌] Profile {profile_path.name} is still Unhealthy.")
        return False


def main():
    print("\n=================================")
    print("      ACTIVE PROFILE MANAGER     ")
    print("=================================")
    
    while True:
        try:
            desired = int(input("\nHow many profiles do you need for this session? ").strip())
            if desired > 0:
                break
        except ValueError:
            print("Please enter a valid number.")
            
    profiles = discover_profiles()
    healthy = []
    
    print("\n--- Initial Health Check ---")
    for p in profiles:
        user_data_dir = str(p / "User Data")
        if not (p / "User Data").exists():
            shutil.rmtree(p, ignore_errors=True)
            continue
            
        if check_extension_installed(user_data_dir):
            healthy.append(p)
            print(f"  [✅] {p.name} is healthy.")
        else:
            print(f"  [❌] {p.name} is unhealthy. Deleting...")
            shutil.rmtree(p, ignore_errors=True)

    while len(healthy) < desired:
        idx = 1
        while (get_base_dir() / f"ChromeUserData{idx}").exists():
            idx += 1
        new_prof = get_base_dir() / f"ChromeUserData{idx}"
        print(f"\nCreating new profile: {new_prof.name} ({len(healthy)+1}/{desired})")
        if fix_or_create_profile(new_prof):
            healthy.append(new_prof)
            
    healthy_paths = [str(p) for p in healthy]
    with open(HEALTHY_PROFILES_FILE, 'w') as f:
        json.dump(healthy_paths, f)
    print(f"\n[+] Saved {len(healthy_paths)} profiles to {HEALTHY_PROFILES_FILE}.")
    print("\nStarting continuous monitoring. The pipeline can now be started!")
    
    admin_dir = os.path.dirname(HEALTHY_PROFILES_FILE)
    pause_flag = os.path.join(admin_dir, 'PAUSE_FLAG')
    
    while True:
        print("\nSleeping for 20 minutes before next health check...")
        time.sleep(20 * 60)
        
        print("\n--- Initiating Periodic Health Check ---")
        with open(pause_flag, 'w') as f: f.write("1")
        print("[*] Pause flag set. Waiting for lead.py workers to pause...")
        
        temp_csvs = os.path.join(os.path.dirname(admin_dir), 'temp_csvs')
        os.makedirs(temp_csvs, exist_ok=True)
        
        while True:
            idle_count = 0
            for p in healthy:
                m = re.search(r'ChromeUserData(\d+)', p.name)
                if m:
                    idx = m.group(1)
                    if os.path.exists(os.path.join(temp_csvs, f"profile_{idx}_idle.txt")):
                        idle_count += 1
            if idle_count >= len(healthy):
                break
            print(f"Waiting for workers to idle... ({idle_count}/{len(healthy)})")
            time.sleep(10)
            
        print("[*] All workers paused. Checking health...")
        
        new_healthy = []
        for p in healthy:
            user_data_dir = str(p / "User Data")
            if check_extension_installed(user_data_dir):
                print(f"  [✅] {p.name} is healthy.")
                new_healthy.append(p)
            else:
                print(f"  [❌] {p.name} is unhealthy. Recreating...")
                shutil.rmtree(p, ignore_errors=True)
                time.sleep(2)
                fix_or_create_profile(p)
                new_healthy.append(p)
                
        healthy = new_healthy
        
        healthy_paths = [str(p) for p in healthy]
        with open(HEALTHY_PROFILES_FILE, 'w') as f:
            json.dump(healthy_paths, f)
            
        print("[*] Health check complete. Resuming pipeline...")
        if os.path.exists(pause_flag):
            os.remove(pause_flag)

if __name__ == "__main__":
    main()
