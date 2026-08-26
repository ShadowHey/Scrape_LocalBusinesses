import os
import time
import threading
import queue
import pandas as pd
from pathlib import Path
import os
import json
from pathlib import Path
from my_email import extract_emails_from_url

HISTORY_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'history.json')
CONFIG_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'current_task_config.json')

def get_task_id():
    try:
        with open(CONFIG_JSON, 'r') as f:
            return json.load(f).get('id')
    except: return None
TASK_ID = get_task_id()

def update_history_metrics(emails_found_bool):
    if not TASK_ID or not os.path.exists(HISTORY_JSON): return
    try:
        with open(HISTORY_JSON, 'r') as f:
            hist = json.load(f)
        if TASK_ID in hist:
            m = hist[TASK_ID].setdefault('metrics', {})
            # Update leads scraped counter
            curr_leads = m.get('total_leads_scraped_for_emails', 0)
            m['total_leads_scraped_for_emails'] = curr_leads + 1
            
            # Update emails found counter
            if emails_found_bool:
                curr_emails = m.get('total_emails_found', 0)
                m['total_emails_found'] = curr_emails + 1
                
            # Update resume state
            hist[TASK_ID].setdefault('resume_state', {})['last_processed_lead_index_emails'] = m['total_leads_scraped_for_emails']
                
            with open(HISTORY_JSON, 'w') as f:
                json.dump(hist, f, indent=4)
    except: pass


# Configuration
INPUT_FILE = Path("final_results/aggregated_leads.csv")
OUTPUT_CSV = Path("Emails_Fetched.csv")
NUM_WORKER_THREADS = 50

# Thread-safe queue and file lock
lead_queue = queue.Queue(maxsize=1000)
file_lock = threading.Lock()
processed_count = 0
total_count = 0
start_time = 0

def write_to_csv_with_retry(row_dict):
    """Safely append a single row to the output CSV with retry logic on File Lock."""
    df = pd.DataFrame([row_dict])
    
    while True:
        with file_lock:
            try:
                # If file doesn't exist, write with header, else append without header
                header = not OUTPUT_CSV.exists()
                df.to_csv(OUTPUT_CSV, mode='a', index=False, header=header, encoding='utf-8-sig')
                return # Success
            except PermissionError:
                # File is likely open in Excel
                print(f"⚠️ [File Lock] Cannot write to {OUTPUT_CSV}. It might be open in Excel. Retrying in 5 seconds...")
        
        # Wait outside the lock before retrying
        time.sleep(5)

def email_scraper_worker():
    global processed_count, total_count, start_time
    """Worker thread that continuously pulls leads from the queue and scrapes emails."""
    while True:
        lead = lead_queue.get()
        if lead is None:
            # Poison pill to stop the thread
            break
            
        company_name = lead.get('name', 'Unknown')
        website = lead.get('website', None)
        
        if website and pd.notna(website) and str(website).strip():
            emails = extract_emails_from_url(website)
        else:
            emails = "No Website Provided"
            
        lead['Scraped_Emails'] = emails
        
        # Write results immediately
        write_to_csv_with_retry(lead)
        
        with file_lock:
            found = bool(emails and emails != "No Website Provided" and len(emails) > 5)
            update_history_metrics(found)
            processed_count += 1
            elapsed = time.time() - start_time
            rate = processed_count / elapsed if elapsed > 0 else 0
            eta = (total_count - processed_count) / rate if rate > 0 else 0
            print(f"Emails Fetched: {processed_count}/{total_count} - ETA: {eta/60:.1f} mins", end='\r')
        
        lead_queue.task_done()

import csv

def main():
    global total_count, start_time
    print("\n=======================================")
    print("Starting Sequential Email Scraper Pipeline")
    print("=======================================")
    
    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} does not exist. Please ensure aggregation succeeded.")
        return

    processed_links = set()
    processed_names = set()
    if OUTPUT_CSV.exists():
        try:
            print(f"Found existing output file {OUTPUT_CSV}. Reading to skip already processed leads...")
            with open(OUTPUT_CSV, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'link' in row and row['link']:
                        processed_links.add(str(row['link']))
                    elif 'name' in row and row['name'] and row['name'] != 'Unknown':
                        processed_names.add(str(row['name']))
            print(f"Loaded {len(processed_links) + len(processed_names)} processed identifiers.")
        except Exception as e:
            print(f"Error reading existing output file: {e}. Proceeding without skipping.")

    print(f"Counting new leads in {INPUT_FILE}...")
    total_count = 0
    try:
        with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'link' in row and str(row['link']) in processed_links:
                    continue
                if 'name' in row and str(row['name']) in processed_names and str(row['name']) != 'Unknown':
                    continue
                total_count += 1
    except Exception as e:
        print(f"Error reading {INPUT_FILE}: {e}")
        return

    if total_count == 0:
        print("No new leads to process. Exiting.")
        return
        
    print(f"Found {total_count} leads to process.")
    start_time = time.time()
    
    # Start worker threads
    threads = []
    for _ in range(NUM_WORKER_THREADS):
        t = threading.Thread(target=email_scraper_worker, daemon=True)
        t.start()
        threads.append(t)
        
    print("Starting streaming from CSV...")
    with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'link' in row and str(row['link']) in processed_links:
                continue
            if 'name' in row and str(row['name']) in processed_names and str(row['name']) != 'Unknown':
                continue
            
            if 'website' not in row:
                row['website'] = None
                
            lead_queue.put(row)
            
    # Wait for all tasks to complete
    lead_queue.join()
    
    # Send poison pill to stop workers
    for _ in range(NUM_WORKER_THREADS):
        lead_queue.put(None)
        
    for t in threads:
        t.join()
        
    print(f"\n\n=======================================")
    print(f"Email Scraping Complete! Results saved to {OUTPUT_CSV}")
    print("=======================================")

if __name__ == '__main__':
    main()
