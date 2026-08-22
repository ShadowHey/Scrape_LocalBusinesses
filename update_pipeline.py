import re
import os

filepath = r"C:\Users\DhruvBisht\Desktop\Firecrawl\pipeline_executor.py"
with open(filepath, "r") as f:
    content = f.read()

# Replace update_history with initialize_history and mark_stage_completed
replacement = """
def load_history():
    if os.path.exists(HISTORY_JSON):
        try:
            with open(HISTORY_JSON, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_history(hist):
    with open(HISTORY_JSON, 'w') as f:
        json.dump(hist, f, indent=4)

def initialize_history(task_id, mode):
    hist = load_history()
    if task_id not in hist:
        base = {
            "mode": mode,
            "pipeline_stages": {
                "lead.py_completed": False,
                "aggregate.py_completed": False,
                "archiving_completed": False
            },
            "metrics": {
                "total_leads_found_in_maps": 0
            },
            "resume_state": {
                "current_active_script": ""
            }
        }
        
        if mode in ['emails', 'both']:
            base["pipeline_stages"]["pipeline.py_completed"] = False
            base["pipeline_stages"]["cleaner.py_completed"] = False
            base["metrics"]["total_leads_scraped_for_emails"] = 0
            base["metrics"]["total_emails_found"] = 0
            base["resume_state"]["last_processed_lead_index_emails"] = 0
            
        if mode in ['phones', 'both']:
            base["pipeline_stages"]["find_phone.py_completed"] = False
            base["metrics"]["total_leads_scraped_for_phones"] = 0
            base["metrics"]["total_phones_found"] = 0
            base["resume_state"]["last_processed_lead_index_phones"] = 0
            
        hist[task_id] = base
        save_history(hist)

def mark_stage_completed(task_id, script_name):
    hist = load_history()
    if task_id in hist:
        hist[task_id]["pipeline_stages"][f"{script_name}_completed"] = True
        save_history(hist)

def set_active_script(task_id, script_name):
    hist = load_history()
    if task_id in hist:
        hist[task_id]["resume_state"]["current_active_script"] = script_name
        save_history(hist)

def check_stop_flag():
"""

content = re.sub(r'def update_history.*?def check_stop_flag\(\):', replacement, content, flags=re.DOTALL)

# Update run_script
run_script_replacement = """def run_script(script_name, task_id):
    set_active_script(task_id, script_name)
    
    # Check if already completed
    hist = load_history()
    if hist.get(task_id, {}).get("pipeline_stages", {}).get(f"{script_name}_completed", False):
        print(f"\\n[+] Skipping {script_name} - already completed according to history.json.")
        return True
        
    script_path = os.path.join(BASE_DIR, 'scraper_core', script_name)
    if not os.path.exists(script_path):
        print(f"[!] Error: {script_name} not found in scraper_core.")
        return False
        
    print(f"\\n---> Executing {script_name} <---")
    
    process = subprocess.Popen([sys.executable, script_path])
    
    while process.poll() is None:
        if check_stop_flag():
            print(f"\\n[!] STOP FLAG DETECTED! Terminating {script_name} immediately...")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            return "cancelled"
        time.sleep(1)
        
    if process.returncode == 0:
        mark_stage_completed(task_id, script_name)
        return True
    return False
"""

content = re.sub(r'def run_script.*?def run_executor\(\):', run_script_replacement + '\ndef run_executor():', content, flags=re.DOTALL)

# Update run_executor execution block
run_executor_old = """
        # Determine Pipeline Execution
        try:
            # Step 1 & 2: ALWAYS run Google Maps Scraper and Aggregator first!
            res = run_script('lead.py', task_id, "Collecting data from Google Maps")
            if res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("lead.py failed")
            
            res = run_script('aggregate.py', task_id, "Aggregating Leads")
            if res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("aggregate.py failed")
            
            # Step 3: Run the requested scrapers based on mode
            if mode == 'phones':
                res = run_script('find_phone.py', task_id, "Extracting Phones")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
                
            elif mode == 'emails':
                res = run_script('pipeline.py', task_id, "Extracting Emails")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id, "Cleaning Emails")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
            elif mode == 'both':
                res = run_script('pipeline.py', task_id, "Extracting Emails")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id, "Cleaning Emails")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
                res = run_script('find_phone.py', task_id, "Extracting Phones")
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
                
            # If we get here, the task finished successfully
            update_history(task_id, "Completed")
"""
run_executor_new = """
        # Determine Pipeline Execution
        try:
            initialize_history(task_id, mode)
            
            # Step 1 & 2: ALWAYS run Google Maps Scraper and Aggregator first!
            res = run_script('lead.py', task_id)
            if res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("lead.py failed")
            
            res = run_script('aggregate.py', task_id)
            if res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("aggregate.py failed")
            
            # Step 3: Run the requested scrapers based on mode
            if mode == 'phones':
                res = run_script('find_phone.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
                
            elif mode == 'emails':
                res = run_script('pipeline.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
            elif mode == 'both':
                res = run_script('pipeline.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
                res = run_script('find_phone.py', task_id)
                if res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
"""

content = content.replace(run_executor_old, run_executor_new)

# Add archiving_completed update
archiving_old = """
                import file_manager
                file_manager.archive_task(pending_task)
"""
archiving_new = """
                import file_manager
                file_manager.archive_task(pending_task)
                mark_stage_completed(task_id, "archiving")
"""
content = content.replace(archiving_old, archiving_new)

with open(filepath, "w") as f:
    f.write(content)

print("Updated pipeline_executor.py")
