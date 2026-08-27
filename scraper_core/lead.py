import os
import time
import multiprocessing
import pandas as pd
import json
import re
from pathlib import Path
from urllib.parse import quote, quote_plus
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import network_utils

# =====================================================================
# CONFIGURATION
# =====================================================================

# BROWSER_MODE Options: "visible", "headless", "offscreen"
BROWSER_MODE = "headless"

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'current_task_config.json')
try:
    with open(CONFIG_PATH, 'r') as f:
        _cfg = json.load(f)
        search_terms = _cfg.get("search_terms", [])
        locality_label = _cfg.get("locality", "Unknown")
        zip_codes = _cfg.get("zip_codes", [])
except Exception as e:
    print(f"Warning: Could not load task config: {e}")
    search_terms = []
    locality_label = ""
    zip_codes = []

def discover_extension(context, name_match: str, guess: str = ""):
    EXTENSION_ID_RE = re.compile(r"chrome-extension://([a-p]+)/")
    candidates = []
    if guess: candidates.append(guess)
    for sw in context.service_workers:
        m = EXTENSION_ID_RE.match(sw.url)
        if m and m.group(1) not in candidates: candidates.append(m.group(1))
    for bg in context.background_pages:
        m = EXTENSION_ID_RE.match(bg.url)
        if m and m.group(1) not in candidates: candidates.append(m.group(1))
    for ext_id in candidates:
        manifest = _fetch_manifest(context, ext_id)
        if manifest and name_match.lower() in manifest.get("name", "").lower():
            return ext_id, manifest
    try:
        sw = context.wait_for_event("serviceworker", timeout=15000)
        m = EXTENSION_ID_RE.match(sw.url)
        if m:
            print(f"[DEBUG] Found service worker URL: {sw.url}")
            manifest = _fetch_manifest(context, m.group(1))
            if manifest and name_match.lower() in manifest.get("name", "").lower():
                return m.group(1), manifest
    except PWTimeout:
        print("[DEBUG] wait_for_event('serviceworker') timed out.")
        pass
    raise RuntimeError("Could not find Instant Data Scraper.")

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

def get_extension_service_worker(context, extension_id: str):
    for sw in context.service_workers:
        if sw.url.startswith(f"chrome-extension://{extension_id}/"):
            return sw
    try:
        sw = context.wait_for_event("serviceworker", timeout=5000)
        if sw.url.startswith(f"chrome-extension://{extension_id}/"):
            return sw
    except PWTimeout:
        pass
    raise RuntimeError("Could not find Instant Data Scraper service worker.")

def get_tab_id(sw, tab_url: str) -> int:
    tab_id = sw.evaluate(
        """
        async (tabUrl) => {
            const active = await chrome.tabs.query({active: true, lastFocusedWindow: true});
            if (active.length && active[0].url === tabUrl) return active[0].id;
            const byUrl = await chrome.tabs.query({url: tabUrl});
            if (byUrl.length) return byUrl[0].id;
            return active.length ? active[0].id : null;
        }
        """,
        tab_url,
    )
    if tab_id is None: raise RuntimeError("Could not determine Maps tab id.")
    return tab_id

def cycle_to_correct_table(popup_page) -> bool:
    for _ in range(15):
        headers = popup_page.locator("table thead tr th, table tr:first-child th, table tr:first-child td")
        try:
            first_header = headers.first.inner_text(timeout=5000).strip()
        except PWTimeout:
            first_header = ""
            
        if first_header.lower() == "hfpxzc href":
            return True
            
        button = popup_page.get_by_role("button", name=re.compile("try another table", re.I))
        if button.count() == 0: return False
        button.first.click()
        popup_page.wait_for_timeout(500)
    return False

def open_popup_and_crawl(context, extension_id, sw, maps_page, destination_csv: Path):
    tab_id = get_tab_id(sw, maps_page.url)
    popup_url = f"chrome-extension://{extension_id}/src/popup.html?tabid={tab_id}&url={quote(maps_page.url, safe='')}"
    
    popup = context.new_page()
    popup.goto(popup_url)
    popup.wait_for_load_state("domcontentloaded")
    
    try:
        if BROWSER_MODE == "visible":
            maps_page.bring_to_front()
        if not cycle_to_correct_table(popup):
            print("Could not find correct table")
            return False
            
        checkbox = popup.get_by_role("checkbox", name=re.compile("infinite scroll", re.I))
        if checkbox.count() > 0 and not checkbox.first.is_checked():
            checkbox.first.check()
            
        delay_container = popup.get_by_text(re.compile("max delay", re.I)).locator("..")
        delay_container.locator("input").first.fill("60")
        
        if BROWSER_MODE == "visible":
            maps_page.bring_to_front()
        popup.get_by_role("button", name=re.compile("start crawling", re.I)).first.click()
        
        popup.get_by_text(re.compile(r"crawling stopped\.\s*please download data or continue crawling\.", re.I)).first.wait_for(state="visible", timeout=30 * 60 * 1000)
        
        with popup.expect_download(timeout=30_000) as dl_info:
            popup.get_by_text(re.compile(r"\bcsv\b", re.I)).first.click()
        
        download = dl_info.value
        destination_csv.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(destination_csv))
        return True
    finally:
        popup.close()

def process_extension_csv(raw_csv_path: Path, master_file: str, zip_code: str):
    if not raw_csv_path.exists():
        return
        
    df = pd.read_csv(raw_csv_path)
    
    rename_map = {}
    for col in df.columns:
        c_lower = col.lower().strip()
        if c_lower == 'hfpxzc href':
            rename_map[col] = 'link'
        elif c_lower == 'qbf1pd':
            rename_map[col] = 'name'
        elif c_lower == 'w4efsd':
            rename_map[col] = 'rating_or_category'
        elif 'address' in c_lower:
            rename_map[col] = 'address'
    
    df.rename(columns=rename_map, inplace=True)
    
    if 'link' not in df.columns:
        return
    if 'name' not in df.columns:
        df['name'] = "Unknown"
        
    df['source_zip'] = zip_code
    df['tag'] = 'extension_scrape'
    
    if os.path.exists(master_file):
        master_df = pd.read_csv(master_file)
        master_df = pd.concat([master_df, df], ignore_index=True)
    else:
        master_df = df
        
    master_df.drop_duplicates(subset=['link'], inplace=True)
    master_df.to_csv(master_file, index=False)

def build_maps_url(query: str) -> str:
    return f"https://www.google.com/maps/search/{quote_plus(query)}"

import queue

def launch_browser(p, profile_idx, user_data_dir, profile_directory="Default"):
    is_headless = (BROWSER_MODE == "headless")
    
    browser_args = [
        f"--profile-directory={profile_directory}",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--blink-settings=imagesEnabled=false",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows"
    ]
    
    if BROWSER_MODE == "offscreen":
        browser_args.append("--window-position=-10000,-10000")
        
    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="chrome",
        headless=is_headless,
        args=browser_args,
        viewport=None,
        timeout=30_000,
        ignore_default_args=[
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
        ],
    )
    context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
    extension_id, manifest = discover_extension(context, "Instant Data Scraper", "ofaokhiedipichpaobibbnahnkdoiiah")
    sw = get_extension_service_worker(context, extension_id)
    maps_page = context.new_page()
    return context, extension_id, sw, maps_page

import csv

def detect_page_state(page):
    """
    Checks the screen instantly up to 30 seconds to determine the state.
    Returns: 'list', 'single', 'no_results', 'captcha', or 'timeout' (if crashed/blank).
    """
    for _ in range(30):
        # 1. List of businesses (has the search result links)
        if page.locator("a.hfpxzc").count() > 0:
            return "list"
            
        # 2. CAPTCHA detection
        try:
            if page.locator('form#captcha-form').count() > 0 or page.locator('iframe[src*="recaptcha"]').count() > 0:
                return "captcha"
            body_text = page.locator("body").inner_text()
            if "unusual traffic from your computer network" in body_text:
                return "captcha"
        except Exception:
            pass
            
        # 3. No Results (Check text in main panel or body)
        try:
            panel_text = page.locator("div[role='main']").inner_text() if page.locator("div[role='main']").count() > 0 else page.locator("body").inner_text()
            if "Google Maps can't find" in panel_text or "We could not find anything" in panel_text or "No results found" in panel_text or "Make sure your search is spelled correctly" in panel_text:
                return "no_results"
        except Exception:
            pass
            
        # 4. Single Result Profile (has h1 title but no list)
        if page.locator("h1.DUwDvf").count() > 0:
            return "single"
            
        page.wait_for_timeout(1000)
        
    return "timeout"

def extract_single_profile(page, csv_path):
    """
    Extracts data from a single business profile and saves it to a CSV format
    that aggregate.py expects.
    """
    name = page.locator("h1.DUwDvf").first.inner_text() if page.locator("h1.DUwDvf").count() > 0 else "Unknown"
    
    address_btn = page.locator('button[data-item-id="address"]').first
    address = address_btn.inner_text().strip() if address_btn.count() > 0 else ""
    
    website_btn = page.locator('a[data-item-id="authority"]').first
    website = website_btn.get_attribute("href") if website_btn.count() > 0 else ""
    
    cat_btn = page.locator('button.DkEaL').first
    category = cat_btn.inner_text().strip() if cat_btn.count() > 0 else ""
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['qbf1pd', 'hfpxzc href', 'address', 'lcr4fd href', 'w4efsd'])
        writer.writerow([name, page.url, address, website, category])


def worker(profile_idx: int, task_queue):
    print(f"\n[Profile {profile_idx}] Starting worker.")
    
    base_user_dir = Path(os.path.expanduser("~"))
    profile_dirs = sorted(base_user_dir.glob(f"ChromeUserData{profile_idx}*"))
    if profile_dirs:
        USER_DATA_DIR = str(profile_dirs[0] / "User Data")
    else:
        USER_DATA_DIR = str(base_user_dir / f"ChromeUserData{profile_idx}" / "User Data")
        
    PROFILE_DIRECTORY = "Default"
    TEMP_DIR = Path("temp_csvs")
    TEMP_DIR.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        try:
            context, extension_id, sw, maps_page = launch_browser(p, profile_idx, USER_DATA_DIR, PROFILE_DIRECTORY)
        except Exception as e:
            print(f"[Profile {profile_idx}] Fatal error launching browser: {e}")
            return
            
        tasks_since_restart = 0
            
        captcha_strikes = 0
        try:
            while True:
                pause_flag_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'PAUSE_FLAG')
                if os.path.exists(pause_flag_path):
                    print(f"[Profile {profile_idx}] Pause flag detected. Closing browser for health check...")
                    try: context.close()
                    except: pass
                    
                    idle_marker = TEMP_DIR / f"profile_{profile_idx}_idle.txt"
                    with open(idle_marker, "w") as f: f.write("1")
                    
                    while os.path.exists(pause_flag_path):
                        time.sleep(2)
                        
                    if idle_marker.exists():
                        try: idle_marker.unlink()
                        except: pass
                        
                    print(f"[Profile {profile_idx}] Resuming after health check...")
                    context, extension_id, sw, maps_page = launch_browser(p, profile_idx, USER_DATA_DIR, PROFILE_DIRECTORY)
                    tasks_since_restart = 0

                try:
                    term, zip_code = task_queue.get_nowait()
                except queue.Empty:
                    print(f"[Profile {profile_idx}] No more tasks in queue. Exiting.")
                    break
                    
                if tasks_since_restart >= 5:
                    print(f"[Profile {profile_idx}] Proactively restarting browser to free memory (5 tasks completed)...")
                    try: context.close()
                    except: pass
                    try:
                        context, extension_id, sw, maps_page = launch_browser(p, profile_idx, USER_DATA_DIR, PROFILE_DIRECTORY)
                        tasks_since_restart = 0
                    except Exception as e:
                        print(f"[Profile {profile_idx}] Fatal error during proactive restart: {e}")
                        task_queue.put((term, zip_code))
                        break
                    
                query = f"{term} in {zip_code} {locality_label}".strip()
                raw_csv_path = TEMP_DIR / f"{term.replace(' ', '_')}_{zip_code}.csv"
                
                if raw_csv_path.exists() and raw_csv_path.stat().st_size > 0:
                    print(f"[Profile {profile_idx}] Skipping: {query} (Already processed)")
                    continue
                    
                print(f"[Profile {profile_idx}] Searching: {query}")
                network_utils.wait_for_network()
                
                try:
                    url = build_maps_url(query)
                    maps_page.goto(url, wait_until="domcontentloaded")
                    
                    state = detect_page_state(maps_page)
                    print(f"[Profile {profile_idx}] State: {state}")
                    
                    if state in ["no_results", "single", "list"]:
                        captcha_strikes = 0
                        
                    if state == "no_results":
                        print(f"  -> Skipping '{query}' (0 results)")
                        tasks_since_restart += 1
                        continue
                        
                    elif state == "single":
                        print(f"  -> Extracting single profile directly")
                        extract_single_profile(maps_page, raw_csv_path)
                        print(f"  -> Extracted to {raw_csv_path.name}")
                        tasks_since_restart += 1
                        continue
                        
                    elif state == "list":
                        if BROWSER_MODE == "visible":
                            maps_page.bring_to_front()
                        
                        success = open_popup_and_crawl(context, extension_id, sw, maps_page, raw_csv_path)
                        
                        if success:
                            print(f"  -> Extracted to {raw_csv_path.name}")
                            tasks_since_restart += 1
                            
                    elif state == "captcha":
                        raise Exception("CAPTCHA_DETECTED")
                    else:
                        raise Exception("Timeout waiting for map elements (Possible Bot Challenge or Crash)")
                        
                except Exception as e:
                    print(f"  Error on '{query}': {e}")
                    if not network_utils.is_internet_available():
                        network_utils.wait_for_network()
                        print(f"  Retrying '{query}' after network restored...")
                        task_queue.put((term, zip_code))
                    else:
                        captcha_strikes += 1
                        error_type = "CAPTCHA" if str(e) == "CAPTCHA_DETECTED" else "Timeout/Crash"
                        print(f"  [Profile {profile_idx}] {error_type} strike {captcha_strikes}/3. Initiating restart...")
                        task_queue.put((term, zip_code))
                        try: context.close()
                        except: pass
                        
                        if captcha_strikes >= 3:
                            print(f"[Profile {profile_idx}] BURNED (3 consecutive {error_type} errors). Removing from healthy profiles.")
                            admin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin')
                            healthy_json = os.path.join(admin_dir, 'health_profiles.json')
                            safety_limit_json = os.path.join(admin_dir, 'safety_limit.json')
                            
                            try:
                                with open(healthy_json, 'r') as f: paths = json.load(f)
                                paths = [p for p in paths if f"ChromeUserData{profile_idx}" not in p]
                                with open(healthy_json, 'w') as f: json.dump(paths, f)
                                remaining = len(paths)
                            except:
                                remaining = 0
                                
                            try:
                                with open(safety_limit_json, 'r') as f: safety_limit = json.load(f).get("safety_limit", 1)
                            except:
                                safety_limit = 1
                                
                            if remaining < safety_limit:
                                print(f"\nCRITICAL: Healthy profiles dropped below safety limit ({remaining} < {safety_limit}).")
                                print("Task paused and archived. Please run profile_manager.py to generate new profiles before resuming!")
                                with open(os.path.join(admin_dir, 'PIPELINE_PAUSED'), 'w') as f: f.write("PAUSED")
                                with open(os.path.join(admin_dir, 'STOP_FLAG'), 'w') as f: f.write("PAUSE_AND_WAIT")
                                with open(os.path.join(admin_dir, 'NEEDS_PROFILES_FLAG'), 'w') as f: f.write("NEEDS_PROFILES")
                                
                            break
                            
                        try:
                            context, extension_id, sw, maps_page = launch_browser(p, profile_idx, USER_DATA_DIR, PROFILE_DIRECTORY)
                            tasks_since_restart = 0
                        except Exception as crash_e:
                            print(f"[Profile {profile_idx}] Fatal error during reactive recovery: {crash_e}")
                            break
        finally:
            try: context.close()
            except: pass

def run():
    print(f"Launching Orchestrator for {len(search_terms)} terms across {len(zip_codes)} zip codes in {locality_label}")
    import multiprocessing
    import json
    import os
    import re
    
    healthy_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'admin', 'health_profiles.json')
    healthy_idx = []
    if os.path.exists(healthy_json):
        try:
            with open(healthy_json, 'r') as f:
                paths = json.load(f)
                for p in paths:
                    m = re.search(r'ChromeUserData(\d+)', p)
                    if m:
                        healthy_idx.append(int(m.group(1)))
        except Exception as e:
            print(f"Failed to load healthy profiles: {e}")
            
    if not healthy_idx:
        print("[!] No healthy profiles found. Defaulting to 1.")
        healthy_idx = [1]
        
    num_profiles = len(healthy_idx)
    
    manager = multiprocessing.Manager()
    task_queue = manager.Queue()
    
    for term in search_terms:
        for zip_code in zip_codes:
            task_queue.put((term, zip_code))
        
    print(f"\n=======================================================")
    print(f"Starting browser pool with up to {num_profiles} profiles.")
    print(f"=======================================================")
    
    processes = []
    total_tasks = len(search_terms) * len(zip_codes)
    active_workers = min(num_profiles, total_tasks)
    for i in range(active_workers):
        profile_idx = healthy_idx[i]
        p = multiprocessing.Process(target=worker, args=(profile_idx, task_queue))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
            
    print("\nAll map scraping complete!")

if __name__ == '__main__':
    run()
