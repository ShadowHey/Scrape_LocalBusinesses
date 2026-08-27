import os
import time
import re
import pandas as pd
from pathlib import Path
import json
import csv
import multiprocessing
import queue
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import socket

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
HISTORY_JSON = os.path.join(ADMIN_DIR, 'history.json')
CONFIG_JSON = os.path.join(ADMIN_DIR, 'current_task_config.json')

def get_task_id():
    try:
        with open(CONFIG_JSON, 'r') as f:
            return json.load(f).get('id')
    except: return None
TASK_ID = get_task_id()

def update_history_metrics(phone_found_bool, write_lock):
    if not TASK_ID or not os.path.exists(HISTORY_JSON): return
    with write_lock:
        try:
            with open(HISTORY_JSON, 'r') as f:
                hist = json.load(f)
            if TASK_ID in hist:
                m = hist[TASK_ID].setdefault('metrics', {})
                curr_leads = m.get('total_leads_scraped_for_phones', 0)
                m['total_leads_scraped_for_phones'] = curr_leads + 1
                if phone_found_bool:
                    curr_phones = m.get('total_phones_found', 0)
                    m['total_phones_found'] = curr_phones + 1
                hist[TASK_ID].setdefault('resume_state', {})['last_processed_lead_index_phones'] = m['total_leads_scraped_for_phones']
                with open(HISTORY_JSON, 'w') as f:
                    json.dump(hist, f, indent=4)
        except: pass

INPUT_FILE = Path("final_results/aggregated_leads.csv")
OUTPUT_CSV = Path("Scraped_Phones.csv")

def detect_page_state(page):
    for _ in range(15):
        if page.locator("h1").count() > 0:
            return "ready"
        try:
            if page.locator('form#captcha-form').count() > 0 or page.locator('iframe[src*="recaptcha"]').count() > 0:
                return "captcha"
            body_text = page.locator("body").inner_text()
            if "unusual traffic from your computer network" in body_text:
                return "captcha"
        except: pass
        page.wait_for_timeout(1000)
    return "timeout"

def extract_phone_and_name(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded")
        state = detect_page_state(page)
        
        if state == "captcha":
            return "CAPTCHA", "CAPTCHA_DETECTED"
        elif state == "timeout":
            return "TIMEOUT", "Timeout waiting for map elements"
            
        time.sleep(1)
        name_element = page.locator("h1").first
        name = name_element.inner_text() if name_element.count() > 0 else "Unknown"
        
        if "can't reach the internet" in name.lower() or "no internet" in name.lower():
            return "NETWORK_ERROR", "Internet disconnected"
            
        phone_button = page.locator('button[data-item-id^="phone:"]').first
        if phone_button.count() > 0:
            phone_text = phone_button.inner_text()
            phone = re.sub(r'[^\d\+\-\s\(\)]', '', phone_text).strip()
        else:
            phone = "No Phone Found"
            
        return name, phone
    except Exception as e:
        err_msg = str(e)
        if "ERR_INTERNET_DISCONNECTED" in err_msg or "ERR_NETWORK_CHANGED" in err_msg or "timeout" in err_msg.lower():
            if not check_internet():
                return "NETWORK_ERROR", "Internet disconnected"
        return "ERROR", err_msg

def launch_browser(p, profile_idx, user_data_dir):
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="chrome",
        headless=True,  # Running in headless mode
        args=[
            "--profile-directory=Default",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--blink-settings=imagesEnabled=false"
        ],
        viewport=None,
        timeout=30000,
        ignore_default_args=["--disable-extensions"]
    )
    # Abort media to save bandwidth
    context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
    page = context.new_page()
    return context, page

def worker(profile_idx, task_queue, write_lock):
    print(f"\n[Profile {profile_idx}] Starting phone extraction worker.")
    
    base_user_dir = Path(os.path.expanduser("~"))
    profile_dirs = sorted(base_user_dir.glob(f"ChromeUserData{profile_idx}*"))
    if profile_dirs:
        USER_DATA_DIR = str(profile_dirs[0] / "User Data")
    else:
        USER_DATA_DIR = str(base_user_dir / f"ChromeUserData{profile_idx}" / "User Data")
        
    with sync_playwright() as p:
        try:
            context, page = launch_browser(p, profile_idx, USER_DATA_DIR)
        except Exception as e:
            print(f"[Profile {profile_idx}] Fatal error launching browser: {e}")
            return
            
        tasks_since_restart = 0
        captcha_strikes = 0
        
        try:
            while True:
                # Pause flag handling
                pause_flag_path = os.path.join(ADMIN_DIR, 'PAUSE_FLAG')
                if os.path.exists(pause_flag_path):
                    print(f"[Profile {profile_idx}] Pause flag detected. Closing browser for health check...")
                    try: context.close()
                    except: pass
                    while os.path.exists(pause_flag_path):
                        time.sleep(2)
                    context, page = launch_browser(p, profile_idx, USER_DATA_DIR)
                    tasks_since_restart = 0

                try:
                    link = task_queue.get_nowait()
                except queue.Empty:
                    print(f"[Profile {profile_idx}] No more links in queue. Exiting.")
                    break
                    
                if tasks_since_restart >= 50:
                    print(f"[Profile {profile_idx}] Proactively restarting browser to free memory (50 links processed)...")
                    try: context.close()
                    except: pass
                    try:
                        context, page = launch_browser(p, profile_idx, USER_DATA_DIR)
                        tasks_since_restart = 0
                    except Exception as e:
                        task_queue.put(link)
                        break

                while True:
                    name, phone = extract_phone_and_name(page, link)
                    if name == "NETWORK_ERROR":
                        print(f"\n[NETWORK ERROR]. Waiting for internet connection to resume...")
                        while not check_internet(): time.sleep(5)
                        print("[+] Internet restored! Retrying...")
                        time.sleep(2)
                        continue
                    break
                    
                if name in ["CAPTCHA", "TIMEOUT", "ERROR"]:
                    error_type = name
                    captcha_strikes += 1
                    print(f"  [Profile {profile_idx}] {error_type} strike {captcha_strikes}/3 on {link}. Restarting...")
                    task_queue.put(link)
                    try: context.close()
                    except: pass
                    
                    if captcha_strikes >= 3:
                        print(f"[Profile {profile_idx}] BURNED (3 {error_type} errors). Removing from healthy profiles.")
                        healthy_json = os.path.join(ADMIN_DIR, 'health_profiles.json')
                        safety_limit_json = os.path.join(ADMIN_DIR, 'safety_limit.json')
                        
                        try:
                            with open(healthy_json, 'r') as f: paths = json.load(f)
                            paths = [pt for pt in paths if f"ChromeUserData{profile_idx}" not in pt]
                            with open(healthy_json, 'w') as f: json.dump(paths, f)
                            remaining = len(paths)
                        except: remaining = 0
                            
                        try:
                            with open(safety_limit_json, 'r') as f: safety_limit = json.load(f).get("safety_limit", 1)
                        except: safety_limit = 1
                            
                        if remaining < safety_limit:
                            print(f"\nCRITICAL: Healthy profiles dropped below safety limit ({remaining} < {safety_limit}).")
                            with open(os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED'), 'w') as f: f.write("PAUSED")
                            with open(os.path.join(ADMIN_DIR, 'STOP_FLAG'), 'w') as f: f.write("PAUSE_AND_WAIT")
                            with open(os.path.join(ADMIN_DIR, 'NEEDS_PROFILES_FLAG'), 'w') as f: f.write("NEEDS_PROFILES")
                        break
                        
                    try:
                        context, page = launch_browser(p, profile_idx, USER_DATA_DIR)
                        tasks_since_restart = 0
                    except: break
                    continue
                    
                # Success
                captcha_strikes = 0
                tasks_since_restart += 1
                
                print(f"[Profile {profile_idx}] Extracted: {name.encode('ascii', 'ignore').decode('ascii')} -> {phone.encode('ascii', 'ignore').decode('ascii')}")
                
                with write_lock:
                    header = not OUTPUT_CSV.exists()
                    with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        if header:
                            writer.writerow(['Business Name', 'Mobile Number', 'Link'])
                        writer.writerow([name, phone, link])
                        
                # Update history metrics safely
                has_phone = phone != "No Phone Found"
                update_history_metrics(has_phone, write_lock)
                
        finally:
            try: context.close()
            except: pass

def main():
    print("=======================================")
    print("Starting Multi-Profile Phone Extraction (Headless)")
    print("=======================================")
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Please run aggregation first.")
        return
        
    processed_links = set()
    if OUTPUT_CSV.exists():
        try:
            with open(OUTPUT_CSV, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'Link' in row and row['Link']:
                        processed_links.add(str(row['Link']))
            print(f"Found existing output. Skipping {len(processed_links)} processed links.")
        except Exception as e:
            print(f"Could not read {OUTPUT_CSV}: {e}")
            
    # Load healthy profiles
    healthy_json = os.path.join(ADMIN_DIR, 'health_profiles.json')
    healthy_idx = []
    if os.path.exists(healthy_json):
        try:
            with open(healthy_json, 'r') as f:
                paths = json.load(f)
                for p in paths:
                    m = re.search(r'ChromeUserData(\d+)', p)
                    if m: healthy_idx.append(int(m.group(1)))
        except: pass
            
    if not healthy_idx:
        print("[!] No healthy profiles found. Defaulting to 1.")
        healthy_idx = [1]
        
    manager = multiprocessing.Manager()
    task_queue = manager.Queue()
    write_lock = manager.Lock()
    
    # Chunk reading to avoid massive memory usage if file is huge
    queued_count = 0
    for df_chunk in pd.read_csv(INPUT_FILE, chunksize=10000):
        if 'link' not in df_chunk.columns: continue
        for link in df_chunk['link'].dropna():
            link = str(link).strip()
            if link and link not in processed_links:
                task_queue.put(link)
                queued_count += 1
                
    if queued_count == 0:
        print("No new links to process. Exiting.")
        return
        
    num_profiles = len(healthy_idx)
    print(f"\nStarting browser pool with up to {num_profiles} profiles processing {queued_count} links.")
    
    processes = []
    active_workers = min(num_profiles, queued_count)
    for i in range(active_workers):
        profile_idx = healthy_idx[i]
        p = multiprocessing.Process(target=worker, args=(profile_idx, task_queue, write_lock))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
            
    print("\n=======================================")
    print(f"Finished extracting! Results saved to {OUTPUT_CSV}")
    print("=======================================")

if __name__ == "__main__":
    main()
