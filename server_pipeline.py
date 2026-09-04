"""
server_pipeline.py
==================
A single, fully automated pipeline script designed to run on a server
(Linux/Colab/Jupyter) with zero human interaction.

Prerequisites:
  - Run create_golden_profile.py ONCE on your local Windows machine first.
  - Upload the resulting ~/golden_profile folder to this server at ~/golden_profile.
  - A pending task must exist in admin/tasks.json (created via main.py).

Server setup (Linux only, run once):
  pip install pyvirtualdisplay playwright
  playwright install chromium
  apt-get install -y xvfb

Usage:
  python server_pipeline.py
  python server_pipeline.py --num-profiles 5
  python server_pipeline.py --golden-dir /custom/path/golden_profile
"""

import os
import sys
import json
import shutil
import time
import platform
import argparse
import multiprocessing
import queue as queue_module
import re
from pathlib import Path
from datetime import datetime

# ============================================================
# PATH SETUP — makes scraper_core importable
# ============================================================
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SCRAPER_CORE = os.path.join(BASE_DIR, 'scraper_core')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SCRAPER_CORE)

ADMIN_DIR    = os.path.join(BASE_DIR, 'admin')
CONFIG_JSON  = os.path.join(ADMIN_DIR, 'current_task_config.json')
TASKS_JSON   = os.path.join(ADMIN_DIR, 'tasks.json')
HEALTH_JSON  = os.path.join(ADMIN_DIR, 'health_profiles.json')
HISTORY_JSON = os.path.join(ADMIN_DIR, 'history.json')
EXT_PATH     = os.path.join(SCRAPER_CORE, 'ext_unpacked')
WORKER_DIR   = os.path.join(BASE_DIR, 'worker_profiles')

IS_WINDOWS   = platform.system() == "Windows"

# Default golden profile location
DEFAULT_GOLDEN = os.path.join(os.path.expanduser("~"), "golden_profile")

# ============================================================
# ARGUMENT PARSING
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Fully automated scrape pipeline.")
    parser.add_argument(
        "--num-profiles", type=int, default=5,
        help="Number of parallel browser workers (default: 5)"
    )
    parser.add_argument(
        "--golden-dir", type=str, default=DEFAULT_GOLDEN,
        help=f"Path to golden profile folder (default: {DEFAULT_GOLDEN})"
    )
    return parser.parse_args()

# ============================================================
# PHASE 0 — CONFIG LOADING
# ============================================================

def load_config():
    print("\n[Phase 0] Loading task configuration...")

    # Pick the first pending task from tasks.json and write it to current_task_config.json
    if not os.path.exists(TASKS_JSON):
        print(f"  [!] {TASKS_JSON} not found. Create a task with main.py first.")
        sys.exit(1)

    with open(TASKS_JSON, 'r') as f:
        tasks = json.load(f)

    if not isinstance(tasks, list):
        tasks = [tasks]

    pending = next((t for t in tasks if t.get("status") in ["pending", "paused"]), None)
    if not pending:
        print("  [!] No pending tasks found in tasks.json.")
        print("      Create a task with main.py first.")
        sys.exit(1)

    # Write to current_task_config.json (as pipeline_executor.py does)
    with open(CONFIG_JSON, 'w') as f:
        json.dump(pending, f, indent=4)

    print(f"  [OK] Loaded task: {pending['id']} | {pending.get('locality')} | {len(pending.get('zip_codes', []))} zips")
    return pending

# ============================================================
# PHASE 1 — VALIDATE GOLDEN PROFILE
# ============================================================

def validate_golden_profile(golden_dir: str):
    print(f"\n[Phase 1] Validating golden profile at: {golden_dir}")
    if not os.path.isdir(golden_dir):
        print(f"  [!] Golden profile NOT found: {golden_dir}")
        print("      Please run create_golden_profile.py on your Windows machine,")
        print("      then upload the golden_profile folder to this server at:")
        print(f"      {golden_dir}")
        sys.exit(1)
    print("  [OK] Golden profile found.")

# ============================================================
# PHASE 2 — START VIRTUAL DISPLAY (Linux only)
# ============================================================

def start_virtual_display():
    print("\n[Phase 2] Virtual display skipped — Using Chrome's --headless=new mode instead.")
    return None

def stop_virtual_display(display):
    pass

# ============================================================
# PHASE 3 — CLONE PROFILES
# ============================================================

def clone_profiles(golden_dir: str, num_profiles: int) -> list:
    print(f"\n[Phase 3] Cloning {num_profiles} worker profiles from golden profile...")

    if os.path.exists(WORKER_DIR):
        shutil.rmtree(WORKER_DIR, ignore_errors=True)
    os.makedirs(WORKER_DIR)

    profile_paths = []
    for i in range(1, num_profiles + 1):
        dest = os.path.join(WORKER_DIR, f"profile_{i}")
        shutil.copytree(golden_dir, dest)

        # Remove lock files so Chrome can open each clone independently
        for lock_file in Path(dest).rglob("SingletonLock"):
            try:
                lock_file.unlink()
            except Exception:
                pass

        profile_paths.append(dest)
        print(f"  [OK] Cloned profile_{i}")

    # Write paths to health_profiles.json for reference
    with open(HEALTH_JSON, 'w') as f:
        json.dump(profile_paths, f, indent=2)

    print(f"  [OK] {num_profiles} worker profiles ready.")
    return profile_paths

# ============================================================
# PHASE 4 — GOOGLE MAPS SCRAPING
# ============================================================

def _remove_lock(user_data_dir: str):
    lock = Path(user_data_dir) / "SingletonLock"
    if lock.exists():
        try:
            lock.unlink()
        except Exception:
            pass


def _launch_server_browser(p, profile_path: str, ext_path: str):
    """
    Launch Chromium with locally loaded extension and auto-accept T&C.
    """
    from lead import discover_extension, get_extension_service_worker

    user_data_dir = str(Path(profile_path) / "User Data")
    _remove_lock(user_data_dir)

    browser_args = [
        "--headless=new",
        f"--load-extension={ext_path}",
        f"--disable-extensions-except={ext_path}",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--blink-settings=imagesEnabled=false",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
    ]

    context = p.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        # No channel="chrome" — use Playwright bundled Chromium for Linux compatibility
        headless=False,
        args=browser_args,
        viewport=None,
        timeout=30_000,
        ignore_default_args=[
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
        ],
    )
    context.route(
        "**/*",
        lambda route: route.abort()
        if route.request.resource_type in ["image", "stylesheet", "font", "media"]
        else route.continue_()
    )

    extension_id, _ = discover_extension(
        context, "Instant Data Scraper", "ofaokhiedipichpaobibbnahnkdoiiah"
    )
    sw = get_extension_service_worker(context, extension_id)
    
    # [CRITICAL FIX] Instantly accept the extension's Terms and Conditions
    # by writing directly to its local storage via the service worker.
    # This bypasses the need for a manually created Windows golden profile!
    try:
        sw.evaluate("chrome.storage.local.set({optIn: true, optInHookShown: true})")
    except Exception as e:
        print(f"      [!] Failed to auto-accept T&C: {e}")

    maps_page = context.new_page()
    return context, extension_id, sw, maps_page


def _server_worker(worker_idx: int, profile_path: str, task_queue, locality_label: str):
    """
    Subprocess worker: scrapes Google Maps for all (term, zip) pairs
    assigned to it from the task_queue.
    """
    # Re-add paths for subprocess context
    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, SCRAPER_CORE)

    from playwright.sync_api import sync_playwright
    from lead import (
        detect_page_state, extract_single_profile,
        open_popup_and_crawl, build_maps_url
    )
    import network_utils

    TEMP_DIR = Path(BASE_DIR) / "temp_csvs"
    TEMP_DIR.mkdir(exist_ok=True)

    print(f"\n[Worker {worker_idx}] Starting.")
    failure_strikes = 0

    with sync_playwright() as p:
        try:
            context, extension_id, sw, maps_page = _launch_server_browser(p, profile_path, EXT_PATH)
        except Exception as e:
            print(f"[Worker {worker_idx}] Fatal launch error: {e}")
            return

        tasks_since_restart = 0

        try:
            while True:
                try:
                    term, zip_code = task_queue.get_nowait()
                except queue_module.Empty:
                    print(f"[Worker {worker_idx}] Queue empty — done.")
                    break

                # Proactive memory restart every 5 tasks
                if tasks_since_restart >= 5:
                    print(f"[Worker {worker_idx}] Proactive restart (5 tasks done)...")
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        context, extension_id, sw, maps_page = _launch_server_browser(p, profile_path, EXT_PATH)
                        tasks_since_restart = 0
                    except Exception as e:
                        print(f"[Worker {worker_idx}] Restart failed: {e}")
                        task_queue.put((term, zip_code))
                        break

                query        = f"{term} in {zip_code} {locality_label}".strip()
                raw_csv_path = TEMP_DIR / f"{term.replace(' ', '_')}_{zip_code}.csv"

                print(f"[Worker {worker_idx}] -> {query}")
                network_utils.wait_for_network()

                try:
                    maps_page.goto(build_maps_url(query), wait_until="domcontentloaded")
                    state = detect_page_state(maps_page)
                    print(f"[Worker {worker_idx}]    State: {state}")

                    if state == "no_results":
                        tasks_since_restart += 1
                        continue
                    elif state == "single":
                        extract_single_profile(maps_page, raw_csv_path)
                        tasks_since_restart += 1
                    elif state == "list":
                        open_popup_and_crawl(
                            context, extension_id, sw, maps_page, raw_csv_path
                        )
                        tasks_since_restart += 1
                    elif state == "captcha":
                        raise Exception("CAPTCHA_DETECTED")
                    else:
                        raise Exception("Timeout/Unknown state")

                    failure_strikes = 0

                except Exception as e:
                    print(f"[Worker {worker_idx}] Error on '{query}': {e}")
                    if not network_utils.is_internet_available():
                        network_utils.wait_for_network()
                        task_queue.put((term, zip_code))
                        continue

                    failure_strikes += 1
                    task_queue.put((term, zip_code))
                    try:
                        context.close()
                    except Exception:
                        pass

                    if failure_strikes >= 3:
                        print(f"[Worker {worker_idx}] 3 consecutive failures — exiting.")
                        break

                    try:
                        context, extension_id, sw, maps_page = _launch_server_browser(p, profile_path, EXT_PATH)
                        tasks_since_restart = 0
                    except Exception as crash_e:
                        print(f"[Worker {worker_idx}] Recovery failed: {crash_e}")
                        break

        finally:
            try:
                context.close()
            except Exception:
                pass

    print(f"[Worker {worker_idx}] Exited.")


def run_maps_scraping(profile_paths: list, config: dict):
    print(f"\n[Phase 4] Google Maps Scraping")

    search_terms  = config.get("search_terms", [])
    zip_codes     = config.get("zip_codes", [])
    locality_label = config.get("locality", "")

    print(f"  Terms: {len(search_terms)} | Zips: {len(zip_codes)} | Workers: {len(profile_paths)}")

    manager    = multiprocessing.Manager()
    task_queue = manager.Queue()

    # Resume support: skip CSVs already written in a previous run
    temp_dir      = os.path.join(BASE_DIR, "temp_csvs")
    completed_set = set()
    if os.path.exists(temp_dir):
        for fname in os.listdir(temp_dir):
            if fname.endswith(".csv"):
                fpath = os.path.join(temp_dir, fname)
                if os.path.getsize(fpath) > 0:
                    completed_set.add(fname)

    tasks_added = 0
    for term in search_terms:
        for zip_code in zip_codes:
            filename = f"{term.replace(' ', '_')}_{zip_code}.csv"
            if filename not in completed_set:
                task_queue.put((term, zip_code))
                tasks_added += 1

    if tasks_added == 0:
        print("  [OK] All scraping tasks already completed — skipping.")
        return

    print(f"  Queuing {tasks_added} tasks ({len(completed_set)} already done).")

    active_workers = min(len(profile_paths), tasks_added)
    processes = []
    for i in range(active_workers):
        proc = multiprocessing.Process(
            target=_server_worker,
            args=(i + 1, profile_paths[i], task_queue, locality_label),
        )
        processes.append(proc)
        proc.start()

    for proc in processes:
        proc.join()

    print("  [OK] All scraping workers finished.")

# ============================================================
# PHASES 6-9 — PIPELINE STAGES (reuse existing scripts)
# ============================================================

def run_aggregation():
    print("\n[Phase 6] Aggregating temp CSVs into aggregated_leads.csv...")
    os.chdir(BASE_DIR)
    from aggregate import aggregate_temp_csvs
    aggregate_temp_csvs()
    print("  [OK] Aggregation complete.")


def run_email_scraping():
    print("\n[Phase 7] Scraping emails from business websites...")
    os.chdir(BASE_DIR)
    import pipeline
    pipeline.main()
    print("  [OK] Email scraping complete.")


def run_cleaning():
    print("\n[Phase 8] Cleaning and deduplicating emails...")
    os.chdir(BASE_DIR)
    from cleaner import run
    run()
    print("  [OK] Cleaning complete.")


def run_segment_formatting():
    print("\n[Phase 9] Formatting segments into uploadable CSVs...")
    os.chdir(BASE_DIR)
    import segment_formatter
    segment_formatter.main()
    print("  [OK] Segment formatting complete.")

# ============================================================
# PHASE 10 — ARCHIVING
# ============================================================

def run_archiving(task: dict):
    print("\n[Phase 10] Archiving results to Logs_NewRuns/...")
    os.chdir(BASE_DIR)
    from file_manager import archive_task

    # Mark task as completed in tasks.json
    if os.path.exists(TASKS_JSON):
        with open(TASKS_JSON, 'r') as f:
            tasks = json.load(f)
        if not isinstance(tasks, list):
            tasks = [tasks]
        tasks = [t for t in tasks if t.get("id") != task.get("id")]
        with open(TASKS_JSON, 'w') as f:
            json.dump(tasks, f, indent=4)

    archive_task(task)
    print("  [OK] Archiving complete.")

# ============================================================
# CLEANUP
# ============================================================

def cleanup_worker_profiles():
    if os.path.exists(WORKER_DIR):
        shutil.rmtree(WORKER_DIR, ignore_errors=True)
        print(f"[Cleanup] Removed worker profiles from {WORKER_DIR}")

# ============================================================
# MAIN ENTRYPOINT
# ============================================================

def main():
    args = parse_args()

    print("\n" + "=" * 55)
    print("   SERVER PIPELINE — Fully Automated Scrape Run")
    print("=" * 55)
    print(f"  Profiles  : {args.num_profiles}")
    print(f"  Golden dir: {args.golden_dir}")
    print(f"  OS        : {platform.system()}")

    # ── Phase 0: Load task config ──────────────────────────────
    task = load_config()

    # ── Phase 1: Validate golden profile ──────────────────────
    validate_golden_profile(args.golden_dir)

    # ── Phase 2: Start virtual display (Linux only) ────────────
    display = start_virtual_display()

    try:
        # ── Phase 3: Clone profiles ────────────────────────────
        profile_paths = clone_profiles(args.golden_dir, args.num_profiles)

        # ── Phase 4: Google Maps scraping ──────────────────────
        run_maps_scraping(profile_paths, task)

    finally:
        # ── Phase 5: Stop virtual display ──────────────────────
        stop_virtual_display(display)
        # Clean up worker profile clones
        cleanup_worker_profiles()

    # ── Phases 6-9: Data pipeline ──────────────────────────────
    run_aggregation()

    mode = task.get("mode", "emails")
    if mode in ["emails", "both"]:
        run_email_scraping()
        run_cleaning()
        run_segment_formatting()

    # ── Phase 10: Archive ──────────────────────────────────────
    run_archiving(task)

    print("\n" + "=" * 55)
    print("   PIPELINE COMPLETE! Check Logs_NewRuns/ for output.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    # Required for Windows multiprocessing
    multiprocessing.freeze_support()
    main()
