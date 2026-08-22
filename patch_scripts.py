import os
import re

BASE_DIR = r"C:\Users\DhruvBisht\Desktop\Firecrawl"
CORE_DIR = os.path.join(BASE_DIR, "scraper_core")

def update_aggregate():
    path = os.path.join(CORE_DIR, "aggregate.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    inject = """
    # Save the aggregated output
    master_df.to_excel(final_output_file, index=False)
    
    # --- Update history.json ---
    try:
        import json
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'current_task_config.json')
        history_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'admin', 'history.json')
        with open(config_path, 'r') as f:
            task_id = json.load(f).get('id')
        if task_id and os.path.exists(history_path):
            with open(history_path, 'r') as f:
                hist = json.load(f)
            if task_id in hist:
                hist[task_id]['metrics']['total_leads_found_in_maps'] = final_count
                with open(history_path, 'w') as f:
                    json.dump(hist, f, indent=4)
    except Exception as e:
        print(f"Warning: Could not update history metrics: {e}")
    # ---------------------------
"""
    if "# --- Update history.json ---" not in content:
        content = content.replace("    # Save the aggregated output\n    master_df.to_excel(final_output_file, index=False)", inject)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("aggregate.py updated")

def update_pipeline():
    path = os.path.join(CORE_DIR, "pipeline.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    top_inject = """import os
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
"""
    
    if "update_history_metrics" not in content:
        content = content.replace("from my_email import extract_emails_from_url", top_inject)
        
        worker_old = """
        lead['Scraped_Emails'] = emails
        
        # Write results immediately
        write_to_csv_with_retry(lead)
        
        with file_lock:
"""
        worker_new = """
        lead['Scraped_Emails'] = emails
        
        # Write results immediately
        write_to_csv_with_retry(lead)
        
        with file_lock:
            found = bool(emails and emails != "No Website Provided" and len(emails) > 5)
            update_history_metrics(found)
"""
        content = content.replace(worker_old, worker_new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("pipeline.py updated")

def update_find_phone():
    path = os.path.join(CORE_DIR, "find_phone.py")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    top_inject = """import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

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
"""
    
    if "update_history_metrics" not in content:
        content = content.replace("from playwright.sync_api import sync_playwright", top_inject)
        
        worker_old = """
        df_out.to_csv(OUTPUT_FILE, mode='a', index=False, header=header, encoding='utf-8-sig')

        print(f"[{i}] Extracted: {name} -> {phone}")
"""
        worker_new = """
        df_out.to_csv(OUTPUT_FILE, mode='a', index=False, header=header, encoding='utf-8-sig')

        print(f"[{i}] Extracted: {name} -> {phone}")
        found = bool(phone and phone != "No Phone Found")
        update_history_metrics(found)
"""
        content = content.replace(worker_old, worker_new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("find_phone.py updated")

if __name__ == '__main__':
    update_aggregate()
    update_pipeline()
    update_find_phone()
