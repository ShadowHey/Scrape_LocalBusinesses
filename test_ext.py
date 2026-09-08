import os
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXT_PATH = os.path.join(BASE_DIR, 'scraper_core', 'ext_unpacked')
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), "test_profile_sw")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        channel="chrome",
        headless=False,
        args=[
            f"--load-extension={EXT_PATH}",
            f"--disable-extensions-except={EXT_PATH}",
        ],
        ignore_default_args=[
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
        ],
    )
    
    extension_id = None
    for _ in range(30):
        for sw in context.service_workers:
            if "chrome-extension://" in sw.url:
                extension_id = sw.url.split("/")[2]
                break
        if extension_id:
            break
        time.sleep(0.5)
        
    print(f"Extension ID: {extension_id}")
    
    if extension_id:
        sw = None
        for worker in context.service_workers:
            if extension_id in worker.url:
                sw = worker
                break
        
        if sw:
            print("Found SW, opening options page...")
            sw.evaluate("chrome.runtime.openOptionsPage()")
            time.sleep(3)
            print(f"Open pages: {[p.url for p in context.pages]}")
            
    time.sleep(2)
    context.close()
