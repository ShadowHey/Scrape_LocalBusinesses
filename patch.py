import re

with open("scraper_core/lead.py", "r", encoding="utf-8") as f:
    content = f.read()

worker_start = content.find("def worker(profile_idx: int, term: str):")

new_worker = """import queue

def worker(profile_idx: int, task_queue):
    print(f"\\n[Profile {profile_idx}] Starting worker.")
    
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
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                channel="chrome",
                headless=False,
                args=[
                    f"--profile-directory={PROFILE_DIRECTORY}",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--blink-settings=imagesEnabled=false",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows"
                ],
                viewport=None,
                timeout=30_000,
                ignore_default_args=[
                    "--disable-extensions",
                    "--disable-component-extensions-with-background-pages",
                ],
            )
            
            context.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
            
        except PWTimeout:
            print(f"[Profile {profile_idx}] Error: Chrome did not start within 30 seconds.")
            return
            
        try:
            extension_id, manifest = discover_extension(context, "Instant Data Scraper", "ofaokhiedipichpaobibbnahnkdoiiah")
            sw = get_extension_service_worker(context, extension_id)
            maps_page = context.new_page()
            
            while True:
                try:
                    term = task_queue.get_nowait()
                except queue.Empty:
                    print(f"[Profile {profile_idx}] No more terms in queue. Exiting.")
                    break
                    
                print(f"\\n[Profile {profile_idx}] Processing term: '{term}'")
                zip_codes_list = list(zip_codes)
                idx = 0
                while idx < len(zip_codes_list):
                    zip_code = zip_codes_list[idx]
                    query = f"{term} in {zip_code}"
                    raw_csv_path = TEMP_DIR / f"{term.replace(' ', '_')}_{zip_code}.csv"
                    
                    if raw_csv_path.exists() and raw_csv_path.stat().st_size > 0:
                        print(f"[Profile {profile_idx} - {term}] [{idx + 1}/{len(zip_codes_list)}] Skipping: {query} (Already processed)")
                        idx += 1
                        continue
                        
                    print(f"[Profile {profile_idx} - {term}] [{idx + 1}/{len(zip_codes_list)}] Searching: {query}")
                    network_utils.wait_for_network()
                    
                    try:
                        url = build_maps_url(term, zip_code)
                        maps_page.goto(url, wait_until="domcontentloaded")
                        maps_page.wait_for_selector("a.hfpxzc", timeout=30_000)
                        maps_page.bring_to_front()
                        
                        success = open_popup_and_crawl(context, extension_id, sw, maps_page, raw_csv_path)
                        
                        if success:
                            print(f"  -> Extracted to {raw_csv_path.name}")
                        
                        idx += 1
                            
                    except Exception as e:
                        print(f"  Error on '{query}': {e}")
                        if not network_utils.is_internet_available():
                            network_utils.wait_for_network()
                            print(f"  Retrying '{query}' after network restored...")
                        else:
                            idx += 1
                            
                        try: maps_page.close()
                        except: pass
                        maps_page = context.new_page()
                    
        except Exception as e:
            print(f"[Profile {profile_idx}] Fatal error: {e}")
        finally:
            context.close()
"""

new_run = """def run():
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
        task_queue.put(term)
        
    print(f"\\n=======================================================")
    print(f"Starting browser pool with up to {num_profiles} profiles.")
    print(f"=======================================================")
    
    processes = []
    active_workers = min(num_profiles, len(search_terms))
    for i in range(active_workers):
        profile_idx = healthy_idx[i]
        p = multiprocessing.Process(target=worker, args=(profile_idx, task_queue))
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join()
            
    print("\\nAll map scraping complete!")

if __name__ == '__main__':
    run()
"""

content = content[:worker_start] + new_worker + "\\n\\n" + new_run

with open("scraper_core/lead.py", "w", encoding="utf-8") as f:
    f.write(content)
print("done")
