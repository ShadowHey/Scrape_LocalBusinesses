import os
import time
import re
import pandas as pd
from pathlib import Path
import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import socket

def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Check if internet is available."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False

HISTORY_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'history.json')
CONFIG_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'current_task_config.json')

def get_task_id():
    try:
        with open(CONFIG_JSON, 'r') as f:
            return json.load(f).get('id')
    except: return None
TASK_ID = get_task_id()

def update_history_metrics(phone_found_bool):
    if not TASK_ID or not os.path.exists(HISTORY_JSON): return
    try:
        with open(HISTORY_JSON, 'r') as f:
            hist = json.load(f)
        if TASK_ID in hist:
            m = hist[TASK_ID].setdefault('metrics', {})
            # Update leads scraped counter
            curr_leads = m.get('total_leads_scraped_for_phones', 0)
            m['total_leads_scraped_for_phones'] = curr_leads + 1
            
            # Update phones found counter
            if phone_found_bool:
                curr_phones = m.get('total_phones_found', 0)
                m['total_phones_found'] = curr_phones + 1
                
            # Update resume state
            hist[TASK_ID].setdefault('resume_state', {})['last_processed_lead_index_phones'] = m['total_leads_scraped_for_phones']
                
            with open(HISTORY_JSON, 'w') as f:
                json.dump(hist, f, indent=4)
    except: pass


INPUT_FILE = Path("final_results/aggregated_leads.csv")
OUTPUT_CSV = Path("Scraped_Phones.csv")

def extract_phone_and_name(page, url):
    """
    Navigates to the Google Maps URL and extracts the business name and phone number.
    """
    try:
        page.goto(url, timeout=60000)
        # Wait for the main panel to load (the h1 is a good indicator)
        page.wait_for_selector("h1", timeout=15000)
        time.sleep(1) # Give it a brief moment to render fully
        
        # Extract name
        name_element = page.locator("h1").first
        name = name_element.inner_text() if name_element.count() > 0 else "Unknown"
        
        # Check for network error in the page content
        if "can't reach the internet" in name.lower() or "no internet" in name.lower():
            return "NETWORK_ERROR", "Google Maps can't reach the internet"
            
        # Extract phone
        # Usually it's in a button with data-item-id starting with "phone:"
        phone_button = page.locator('button[data-item-id^="phone:"]').first
        if phone_button.count() > 0:
            phone_text = phone_button.inner_text()
            # Clean up the phone text if it has extra words or icons
            phone = re.sub(r'[^\d\+\-\s\(\)]', '', phone_text).strip()
        else:
            # Fallback: find any div/button with a phone icon or text matching a pattern
            # For simplicity, we just say No Phone Found if the specific selector misses
            phone = "No Phone Found"
            
        return name, phone
    except Exception as e:
        err_msg = str(e)
        if "ERR_INTERNET_DISCONNECTED" in err_msg or "ERR_NETWORK_CHANGED" in err_msg or "timeout" in err_msg.lower():
            if not check_internet():
                return "NETWORK_ERROR", "Internet disconnected"
        print(f"Error extracting {url}: {e}")
        return "Unknown", "Error"

def main():
    print("=======================================")
    print("Starting Phone Extraction via Playwright")
    print("=======================================")
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Please run aggregation first.")
        return
        
    processed_links = set()
    if OUTPUT_CSV.exists():
        try:
            # We can read existing output without chunking since it's usually smaller, or chunk it if needed.
            # Assuming output is manageable, or just use python csv.
            import csv
            with open(OUTPUT_CSV, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'Link' in row and row['Link']:
                        processed_links.add(str(row['Link']))
            print(f"Found existing output. Skipping {len(processed_links)} processed links.")
        except Exception as e:
            print(f"Could not read {OUTPUT_CSV}: {e}")
            
    with sync_playwright() as p:
        # Launch a fresh, unauthenticated profile (headful to avoid blocks and show progress)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        processed_count = 0
        
        for df_chunk in pd.read_csv(INPUT_FILE, chunksize=5000):
            if 'link' not in df_chunk.columns:
                continue
                
            for index, row in df_chunk.iterrows():
                link = str(row.get('link', ''))
                
                if not link or link == 'nan':
                    continue
                    
                if link in processed_links:
                    continue
                    
                while True:
                    name, phone = extract_phone_and_name(page, link)
                    if name == "NETWORK_ERROR":
                        print(f"\n[NETWORK ERROR] {phone}. Waiting for internet connection to resume...")
                        while not check_internet():
                            time.sleep(5)
                        print("[+] Internet restored! Retrying phone extraction...")
                        time.sleep(2)
                        continue
                    break
                
            # Save incrementally
            row_dict = {
                'Business Name': name,
                'Mobile Number': phone,
                'Link': link
            }
            
            out_df = pd.DataFrame([row_dict])
            header = not OUTPUT_CSV.exists()
            
            # Use retry loop if file is locked
            while True:
                try:
                    out_df.to_csv(OUTPUT_CSV, mode='a', index=False, header=header, encoding='utf-8-sig')
                    break
                except PermissionError:
                    print(f"\n[WARNING] Cannot write to {OUTPUT_CSV} (File may be open). Retrying in 5 seconds...")
                    time.sleep(5)
            
            processed_count += 1
            # Using ascii compatible print
            print(f"[{processed_count}] Extracted: {name.encode('ascii', 'ignore').decode('ascii')} -> {phone.encode('ascii', 'ignore').decode('ascii')}")
            
            # Small delay to be gentle on Google Maps
            time.sleep(1)
            
        browser.close()
        
    print("\n=======================================")
    print(f"Finished extracting! Results saved to {OUTPUT_CSV}")
    print("=======================================")

if __name__ == "__main__":
    main()
