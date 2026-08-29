import json
import os
import time
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
TASKS_JSON = os.path.join(ADMIN_DIR, 'tasks.json')
TASK_IDS_TXT = os.path.join(ADMIN_DIR, 'Task_Ids.txt')
CONFIG_JSON = os.path.join(ADMIN_DIR, 'current_task_config.json')
STOP_FLAG = os.path.join(ADMIN_DIR, 'STOP_FLAG')
HISTORY_JSON = os.path.join(ADMIN_DIR, 'history.json')

def load_tasks():
    if os.path.exists(TASKS_JSON):
        with open(TASKS_JSON, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_tasks(tasks):
    with open(TASKS_JSON, 'w') as f:
        json.dump(tasks, f, indent=4)


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
            base["pipeline_stages"]["segment_formatter.py_completed"] = False
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

def validate_pipeline_stage_from_files(task_id, mode):
    hist = load_history()
    if task_id not in hist:
        return

    stages = hist[task_id]["pipeline_stages"]
    
    # Check if we can safely assume stages completed based on final output files
    # final_results/aggregated_leads.csv implies aggregate.py finished
    if os.path.exists(os.path.join(BASE_DIR, 'final_results', 'aggregated_leads.csv')):
        if not stages.get("lead.py_completed"):
            print("[*] Found aggregated_leads.csv, marking lead.py as completed.")
            stages["lead.py_completed"] = True
            
    # FinalEmails.csv implies cleaner.py finished, which implies pipeline.py finished
    if os.path.exists(os.path.join(BASE_DIR, 'FinalEmails.csv')):
        if not stages.get("pipeline.py_completed") and mode in ['emails', 'both']:
            print("[*] Found FinalEmails.csv, marking pipeline.py as completed.")
            stages["pipeline.py_completed"] = True
        if not stages.get("cleaner.py_completed") and mode in ['emails', 'both']:
            print("[*] Found FinalEmails.csv, marking cleaner.py as completed.")
            stages["cleaner.py_completed"] = True

    hist[task_id]["pipeline_stages"] = stages
    save_history(hist)

class PauseAndExitError(Exception):
    pass

class PauseAndWaitError(Exception):
    pass

def check_stop_flag():
    if os.path.exists(STOP_FLAG):
        with open(STOP_FLAG, 'r') as f:
            content = f.read().strip()
        os.remove(STOP_FLAG)
        if content == "PAUSE_AND_EXIT":
            return "PAUSE_AND_EXIT"
        elif content == "PAUSE_AND_WAIT":
            return "PAUSE_AND_WAIT"
        return True
    return False

def run_script(script_name, task_id):
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
        
    print(f"\n---> Executing {script_name} <---")
    
    process = subprocess.Popen([sys.executable, script_path])
    
    while process.poll() is None:
        stop_status = check_stop_flag()
        if stop_status:
            print(f"\n[!] STOP FLAG DETECTED! Terminating {script_name} immediately...")
            try:
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                process.kill()
            if stop_status == "PAUSE_AND_EXIT":
                return "PAUSE_AND_EXIT"
            elif stop_status == "PAUSE_AND_WAIT":
                return "PAUSE_AND_WAIT"
            return "cancelled"
        time.sleep(1)
        
    if process.returncode == 0:
        mark_stage_completed(task_id, script_name)
        return True
    return False

def is_pipeline_paused():
    pause_flag = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')
    return os.path.exists(pause_flag)

def run_executor():
    print("Task Executor started. Waiting for pending tasks...")
    was_paused = False
    while True:
        if is_pipeline_paused():
            if not was_paused:
                print("\n[i] Pipeline is currently PAUSED. Waiting for Resume command from main menu...")
                was_paused = True
            time.sleep(2)
            continue
            
        if was_paused:
            print("\n[+] Pipeline Resumed! Scanning for tasks...")
            was_paused = False
            
        tasks = load_tasks()
        pending_task = None
        task_idx = -1
        
        for i, t in enumerate(tasks):
            if t.get('status') == 'running':
                pending_task = t
                task_idx = i
                print(f"\\n[*] Found an INTERRUPTED running task: {pending_task['id']}. Resuming it...")
                break
                
        # Fallback to pending or paused if no running task is found
        if not pending_task:
            for i, t in enumerate(tasks):
                if t.get('status') in ['pending', 'paused']:
                    pending_task = t
                    task_idx = i
                    break
                
        if not pending_task:
            time.sleep(5)
            continue
            
        if pending_task.get('status') != 'running':
            print(f"\\n[*] Found pending task: {pending_task['id']}")
        
        import file_manager
        file_manager.restore_task(pending_task)
        
        # Mark as running
        if 'started_at' not in tasks[task_idx]:
            tasks[task_idx]['started_at'] = datetime.now().isoformat()
            pending_task['started_at'] = tasks[task_idx]['started_at']
            
        tasks[task_idx]['status'] = 'running'
        save_tasks(tasks)
        
        # Dump config for scraper_core modules
        with open(CONFIG_JSON, 'w') as f:
            json.dump(pending_task, f, indent=4)
            
        mode = pending_task.get('mode', 'both')
        task_id = pending_task['id']
        success = True
        was_cancelled = False
        
        was_paused_and_exit = False
        was_paused_and_wait = False
        
        # Determine Pipeline Execution
        try:
            initialize_history(task_id, mode)
            validate_pipeline_stage_from_files(task_id, mode)
            
            # Step 1 & 2: ALWAYS run Google Maps Scraper and Aggregator first!
            res = run_script('lead.py', task_id)
            if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
            elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
            elif res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("lead.py failed")
            
            res = run_script('aggregate.py', task_id)
            if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
            elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
            elif res == "cancelled": raise InterruptedError()
            elif not res: raise Exception("aggregate.py failed")
            
            # Step 3: Run the requested scrapers based on mode
            if mode == 'phones':
                res = run_script('find_phone.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
                
            elif mode == 'emails':
                res = run_script('pipeline.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
                res = run_script('segment_formatter.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("segment_formatter.py failed")
                
            elif mode == 'both':
                res = run_script('pipeline.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("pipeline.py failed")
                
                res = run_script('cleaner.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("cleaner.py failed")
                
                res = run_script('segment_formatter.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("segment_formatter.py failed")
                
                res = run_script('find_phone.py', task_id)
                if res == "PAUSE_AND_EXIT": raise PauseAndExitError()
                elif res == "PAUSE_AND_WAIT": raise PauseAndWaitError()
                elif res == "cancelled": raise InterruptedError()
                elif not res: raise Exception("find_phone.py failed")
                
        except PauseAndExitError:
            print(f"\n[-] Task {task_id} was paused! Archiving and exiting executor...")
            success = False
            was_paused_and_exit = True
        except PauseAndWaitError:
            print(f"\n[-] Task {task_id} was paused! Archiving and waiting for auto-resume...")
            success = False
            was_paused_and_wait = True
        except InterruptedError:
            print(f"\n[-] Task {task_id} was cancelled! Transitioning to the next task in the queue...")
            success = False
            was_cancelled = True
        except KeyboardInterrupt:
            print(f"\n[!] Ctrl+C detected! Archiving stranded task {task_id} safely before shutting down...")
            success = False
            was_paused_and_exit = True
        except Exception as e:
            print(f"\n[!] Task execution interrupted due to error: {e}")
            success = False
            
        # Refresh tasks before saving completion state
        tasks = load_tasks()
        current_idx = next((i for i, t in enumerate(tasks) if t['id'] == task_id), -1)
        
        if success:
            print(f"[+] Task {task_id} completed successfully!")
            if current_idx != -1:
                tasks[current_idx]['status'] = 'completed'
                with open(TASK_IDS_TXT, 'a') as f:
                    f.write(f"{task_id} | {pending_task['locality']} | {datetime.now().isoformat()}\n")
                tasks.pop(current_idx)
            
            import file_manager
            file_manager.archive_task(pending_task)
            mark_stage_completed(task_id, "archiving")
        else:
            if was_paused_and_exit:
                if current_idx != -1:
                    tasks[current_idx]['status'] = 'paused'
                import file_manager
                file_manager.archive_task(pending_task, is_paused=True)
                save_tasks(tasks)
                print("\n[+] Exiting pipeline_executor.py gracefully.")
                sys.exit(0)
            elif was_paused_and_wait:
                if current_idx != -1:
                    tasks[current_idx]['status'] = 'paused'
                import file_manager
                file_manager.archive_task(pending_task, is_paused=True)
                save_tasks(tasks)
                continue
            elif was_cancelled:
                # Make sure it's marked as paused if it wasn't already by main.py
                if current_idx != -1:
                    tasks[current_idx]['status'] = 'paused'
                import file_manager
                file_manager.archive_task(pending_task, is_paused=True)
            else:
                if current_idx != -1 and tasks[current_idx]['status'] == 'running':
                    tasks[current_idx]['status'] = 'error'
                import file_manager
                file_manager.archive_task(pending_task, is_error=True)
                
        save_tasks(tasks)

if __name__ == '__main__':
    try:
        run_executor()
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected. Shutting down executor safely.")
        sys.exit(0)
