import os
import shutil
import json
import re
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

HEALTHY_PROFILES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'health_profiles.json')
EXTENSION_ID = "ofaokhiedipichpaobibbnahnkdoiiah"

def get_base_dir():
    return Path(os.path.expanduser("~"))

def kill_scraper_browsers():
    print("\nChecking for lingering scraper browser processes...")
    try:
        # Use WMIC to get ProcessId and CommandLine of all chrome.exe processes
        result = subprocess.run(
            ['wmic', 'process', 'where', 'name="chrome.exe"', 'get', 'ProcessId,CommandLine'],
            capture_output=True, text=True
        )
        killed_count = 0
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or "ProcessId" in line:
                continue
            
            # Only target chrome processes running from our specific user data directories
            if "ChromeUserData" in line:
                # The PID is usually at the very end of the line
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        try:
                            # Taskkill the specific PID
                            subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                            killed_count += 1
                        except Exception as e:
                            print(f"Failed to kill PID {pid}: {e}")
        
        if killed_count > 0:
            print(f"Successfully killed {killed_count} scraper browser processes.")
        else:
            print("No lingering scraper processes found.")
    except Exception as e:
        print(f"Error checking processes: {e}")

def wipe_old_profiles():
    base_dir = get_base_dir()
    profiles = [p for p in base_dir.glob("ChromeUserData*") if p.is_dir()]
    if profiles:
        print("\nWiping old profiles...")
        for p in profiles:
            print(f"  Deleting {p.name}...")
            try:
                shutil.rmtree(p, ignore_errors=True)
            except Exception as e:
                print(f"  [!] Could not delete {p.name}: {e}")
    else:
        print("\nNo old profiles to delete.")

def create_and_setup_profile(profile_path: Path):
    try:
        import subprocess
        user_data_dir = str(profile_path / "User Data")
        safe_path = user_data_dir.replace('\\', '\\\\')
        ps_cmd = f"Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object {{$_.CommandLine -match '{safe_path}'}} | Invoke-CimMethod -MethodName Terminate"
        subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        lock_file = Path(user_data_dir) / "SingletonLock"
        if lock_file.exists():
            try: lock_file.unlink()
            except: pass
    except: pass
    user_data_dir = str(profile_path / "User Data")
    
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
                page.bring_to_front()
                add_btn = page.locator('button', has_text=re.compile("Add to Chrome", re.I)).first
                add_btn.wait_for(state="visible", timeout=15000)
                add_btn.click(timeout=5000)
                print("Clicked 'Add to Chrome'.")
                
                print("\nAutomating native Chrome popup...")
                import platform
                os_name = platform.system()
                time.sleep(1.5) # wait for popup to appear
                
                if os_name == "Windows":
                    import ctypes
                    # Press Left Arrow (VK_LEFT = 0x25)
                    ctypes.windll.user32.keybd_event(0x25, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(0x25, 0, 2, 0)
                    
                    time.sleep(0.5)
                    # Press Enter (VK_RETURN = 0x0D)
                    ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
                    time.sleep(0.05)
                    ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)
                    print("Windows: Simulated Left Arrow + Enter.")
                    
                elif os_name == "Darwin": # macOS
                    import subprocess
                    # Key code 124 = Right Arrow
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 124'])
                    time.sleep(0.5)
                    # Key code 36 = Enter
                    subprocess.run(['osascript', '-e', 'tell application "System Events" to key code 36'])
                    print("macOS: Simulated Right Arrow + Enter.")
                    
                else:
                    print(f"Unsupported OS for native automation: {os_name}")
                
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
                            # 1. Try to find "Choose All" text/label
                            choose_all = p_page.get_by_text(re.compile("Choose All", re.I))
                            if choose_all.count() > 0:
                                choose_all.first.click(timeout=5000)
                                print("Auto-clicked 'Choose All' on extension page!")
                                time.sleep(1)
                                
                                # 2. Try to find "Confirm & Activate" button/text
                                confirm_btn = p_page.get_by_text(re.compile("Confirm & Activate", re.I))
                                if confirm_btn.count() > 0:
                                    confirm_btn.first.click(timeout=5000)
                                    print("Auto-clicked 'Confirm & Activate' on extension page!")
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
                
        # Verification step removed as requested.

    except Exception as e:
        print(f"Error during setup: {e}")
        return False
        
    return True

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", type=int, help="Automatically create this many profiles without prompting")
    parser.add_argument("--limit", type=int, help="Safety limit for the auto profiles")
    args = parser.parse_args()

    print("\n=================================")
    print("      ACTIVE PROFILE MANAGER     ")
    print("=================================")
    
    if args.auto is not None and args.limit is not None:
        desired = args.auto
        safety_limit = args.limit
        if not (0 <= safety_limit < desired):
            print(f"Error: Safety limit {safety_limit} must be between 0 and {desired - 1}.")
            return
    else:
        while True:
            try:
                desired = int(input("\nHow many profiles do you need to create for this session? ").strip())
                if desired > 0:
                    break
            except ValueError:
                print("Please enter a valid number.")
                
        while True:
            try:
                safety_limit = int(input(f"Enter a safety limit (must be strictly less than {desired}): ").strip())
                if 0 <= safety_limit < desired:
                    break
                else:
                    print(f"Error: Safety limit must be between 0 and {desired - 1}.")
            except ValueError:
                print("Please enter a valid number.")
            
    admin_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin')
    os.makedirs(admin_dir, exist_ok=True)
    with open(os.path.join(admin_dir, 'safety_limit.json'), 'w') as f:
        json.dump({"safety_limit": safety_limit, "desired": desired}, f)
        
    # 1. Kill old scraper browsers so we can delete folders safely
    kill_scraper_browsers()
    time.sleep(2) # Give windows a moment to release locks
    
    # 2. Wipe old folders
    wipe_old_profiles()
    
    # 3. Create N new profiles
    healthy = []
    base_dir = get_base_dir()
    for idx in range(1, desired + 1):
        new_prof = base_dir / f"ChromeUserData{idx}"
        print(f"\nCreating new profile: {new_prof.name} ({idx}/{desired})")
        
        # Create folder structure
        user_data_dir = new_prof / "User Data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        
        if create_and_setup_profile(new_prof):
            print(f"[✅] Profile {new_prof.name} is successfully set up!")
            healthy.append(new_prof)
        else:
            print(f"[❌] Profile {new_prof.name} setup failed.")

    # 4. Save and handoff
    if healthy:
        healthy_paths = [str(p) for p in healthy]
        os.makedirs(os.path.dirname(HEALTHY_PROFILES_FILE), exist_ok=True)
        with open(HEALTHY_PROFILES_FILE, 'w') as f:
            json.dump(healthy_paths, f)
        print(f"\n[+] Saved {len(healthy_paths)} working profiles to {HEALTHY_PROFILES_FILE}.")
        print("[+] Handoff complete. pipeline_executor.py can now use these profiles. Exiting...")
    else:
        print("\n[!] No profiles were successfully created. Exiting...")

if __name__ == "__main__":
    main()
