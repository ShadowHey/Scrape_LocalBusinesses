import json
import os
import sys
import uuid
from datetime import datetime
import importlib.util

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
TASKS_JSON = os.path.join(ADMIN_DIR, 'tasks.json')
HEALTH_PROFILES = os.path.join(ADMIN_DIR, 'health_profiles.json')
TASK_IDS_TXT = os.path.join(ADMIN_DIR, 'Task_Ids.txt')

def load_json(filepath, default_val=list):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_val()
    return default_val()

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def show_menu():
    print("\n" + "="*40)
    print("   TASK SCHEDULER & PIPELINE MANAGER")
    print("="*40)
    print("1. Add a New Task")
    print("2. View Queue / Tasks")
    print("3. Reorder Pending Tasks")
    print("4. Delete a Task")
    print("5. Pause Pipeline and Archive")
    print("6. Resume Pipeline from Paused")
    print("7. Exit")
    print("="*40)
    return input("Select an option [1-7]: ").strip()

def parse_list_input(prompt_text):
    print(f"\n{prompt_text}")
    print("Enter your items line by line. Type 'DONE' on a new line when finished, or paste a python array (e.g. ['A', 'B']):")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == 'DONE':
            break
        lines.append(line.strip())
        
    # If they pasted a python list representation directly (even multi-line)
    joined_text = "".join(lines).strip()
    if joined_text.startswith('[') and joined_text.endswith(']'):
        import ast
        try:
            return ast.literal_eval(joined_text)
        except Exception:
            pass
            
    # Remove empty lines, strip quotes/commas that might come from raw pasting
    cleaned = []
    for l in lines:
        c = l.strip().strip(',').strip('"').strip("'")
        if c and c != '[' and c != ']': 
            cleaned.append(c)
    return cleaned

def parse_set_input(prompt_text):
    print(f"\n{prompt_text}")
    print("Enter items line by line. Type 'DONE' to finish, or paste a set/list:")
    lines = []
    while True:
        line = input()
        if line.strip().upper() == 'DONE':
            break
        lines.append(line.strip())
        
    joined_text = "".join(lines).strip()
    if joined_text.startswith('{') and joined_text.endswith('}'):
        import ast
        try:
            return list(ast.literal_eval(joined_text))
        except Exception:
            pass
    elif joined_text.startswith('[') and joined_text.endswith(']'):
        import ast
        try:
            return ast.literal_eval(joined_text)
        except Exception:
            pass
            
    # Remove empty lines, strip quotes/commas that might come from raw pasting
    cleaned = []
    for l in lines:
        c = l.strip().strip(',').strip('"').strip("'")
        if c and c not in ['[', ']', '{', '}']: 
            cleaned.append(c)
    return cleaned

def add_task():
    print("\n--- Add New Task ---")
    
    # 1. Initial Wording
    initial_wording = input("Enter Initial Wording for Segments (e.g., groupbookings_ or esa_): ").strip()
    
    # 2. Search Terms
    search_terms = parse_list_input("Enter Search Terms (e.g. Public School):")
    if not search_terms:
        print("Error: Search terms cannot be empty.")
        return
        
    # 3. Locality
    locality = input("\nEnter Locality Label (e.g. Texas, Studio6_Fort_Myers): ").strip()
    
    # 3. Zip Codes
    print("\nHow would you like to enter Zip Codes?")
    print("1. Enter manually / Paste list")
    print("2. Select from State (via final_queue_builder)")
    zip_choice = input("Select [1-2]: ").strip()
    
    zip_codes = []
    if zip_choice == '2':
        try:
            import final_queue_builder
            states = list(final_queue_builder.STATE_ZIPS.keys())
            print("\nSelect a State:")
            for i, state in enumerate(states):
                print(f"[{i}] {state}")
            s_idx = input("Enter state number: ").strip()
            if s_idx.isdigit() and int(s_idx) < len(states):
                selected_state = states[int(s_idx)]
                zip_codes = final_queue_builder.STATE_ZIPS[selected_state]
                print(f"[+] Loaded {len(zip_codes)} zip codes for {selected_state}")
            else:
                print("Invalid state selection.")
                return
        except Exception as e:
            print(f"Error loading states: {e}")
            return
    else:
        zip_codes = parse_set_input("Enter Zip Codes:")
        
    if not zip_codes:
        print("Error: Zip codes cannot be empty.")
        return
        
    # 4. Mode
    print("\nSelect Task Mode:")
    print("1. Emails Only")
    print("2. Phones Only")
    print("3. Both (Emails + Phones)")
    mode_choice = input("Select [1-3]: ").strip()
    mode = "both"
    if mode_choice == '1': mode = "emails"
    elif mode_choice == '2': mode = "phones"
    
    # Create Task Object
    task_id = str(uuid.uuid4())[:8]
    task = {
        "id": task_id,
        "created_at": datetime.now().isoformat(),
        "initial_wording": initial_wording,
        "search_terms": search_terms,
        "locality": locality,
        "zip_codes": zip_codes,
        "mode": mode,
        "status": "pending",
        "progress": {
            "completed_zips": [],
            "current_step": "init"
        }
    }
    
    tasks = load_json(TASKS_JSON, list)
    tasks.append(task)
    save_json(TASKS_JSON, tasks)
    
    print(f"\n[+] Task {task_id} added successfully and is now pending.")

def view_queue():
    tasks = load_json(TASKS_JSON, list)
    print("\n--- Current Queue ---")
    if not tasks:
        print("Queue is empty.")
        return
        
    for i, t in enumerate(tasks):
        status = t.get('status', 'pending')
        marker = "[RUNNING]" if status == 'running' else f"[{i}]"
        print(f"{marker} ID: {t['id']} | Mode: {t['mode'].upper()} | Locality: {t['locality']} | Zips: {len(t['zip_codes'])} | Terms: {len(t['search_terms'])} | Status: {status}")

def reorder_queue():
    tasks = load_json(TASKS_JSON, list)
    # Extract only pending tasks, we can't reorder running ones
    running_tasks = [t for t in tasks if t.get('status') == 'running']
    pending_tasks = [t for t in tasks if t.get('status') != 'running']
    
    if not pending_tasks:
        print("\nNo pending tasks to reorder.")
        return
        
    print("\n--- Pending Tasks ---")
    for i, t in enumerate(pending_tasks):
        print(f"[{i}] ID: {t['id']} | Locality: {t['locality']}")
        
    order = input("\nEnter the new order by index, separated by commas (e.g. 2, 0, 1): ")
    try:
        new_indices = [int(x.strip()) for x in order.split(',')]
        if len(new_indices) != len(pending_tasks) or set(new_indices) != set(range(len(pending_tasks))):
            print("Error: You must include all indices exactly once.")
            return
            
        reordered_pending = [pending_tasks[i] for i in new_indices]
        
        # Save back: running tasks first, then reordered pending
        save_json(TASKS_JSON, running_tasks + reordered_pending)
        print("[+] Queue reordered successfully.")
    except Exception as e:
        print(f"Error parsing order: {e}")

def delete_task():
    view_queue()
    tasks = load_json(TASKS_JSON, list)
    if not tasks: return
    
    idx_str = input("\nEnter the index or ID of the task to delete (or type 'cancel' to abort): ").strip()
    if idx_str.lower() == 'cancel': return
    
    target_idx = -1
    if idx_str.isdigit() and int(idx_str) < len(tasks):
        target_idx = int(idx_str)
    else:
        for i, t in enumerate(tasks):
            if t['id'] == idx_str:
                target_idx = i
                break
                
    if target_idx == -1:
        print("Task not found.")
        return
        
    t = tasks[target_idx]
    if t.get('status') == 'running':
        print(f"[!] Deleting currently running task {t['id']}...")
        stop_flag = os.path.join(ADMIN_DIR, 'STOP_FLAG')
        with open(stop_flag, 'w') as f:
            f.write("STOP")
            
        tasks.pop(target_idx)
        print("Task deleted from queue. The executor will stop working on it shortly and move on.")
    else:
        tasks.pop(target_idx)
        print("Task deleted from queue.")
        
    save_json(TASKS_JSON, tasks)

def pause_and_archive_pipeline():
    tasks = load_json(TASKS_JSON, list)
    if not tasks:
        print("Queue is empty.")
        return
        
    running_task_idx = -1
    for i, t in enumerate(tasks):
        if t.get('status') == 'running':
            running_task_idx = i
            break
            
    if running_task_idx == -1:
        print("No task is currently running.")
        return
        
    t = tasks[running_task_idx]
    print(f"\n[!] Pausing and archiving currently running task {t['id']}...")
    
    # Pause the pipeline globally
    pause_flag = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')
    with open(pause_flag, 'w') as f:
        f.write("PAUSED")
        
    # Send exit flag to executor
    stop_flag = os.path.join(ADMIN_DIR, 'STOP_FLAG')
    with open(stop_flag, 'w') as f:
        f.write("PAUSE_AND_EXIT")
        
    t['status'] = 'paused'
    save_json(TASKS_JSON, tasks)
    print("Task set to 'paused' and pipeline paused globally. Pipeline executor will archive and close shortly.")

def resume_paused_pipeline():
    pause_flag = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')
    if os.path.exists(pause_flag):
        os.remove(pause_flag)
        print("\n[+] PIPELINE_PAUSED flag removed. The pipeline is now resumed.")
        print("[i] You can now start 'python pipeline_executor.py' to resume execution from the top of the queue.")
    else:
        print("\n[i] The pipeline is not currently paused.")

def main():
    if not os.path.exists(ADMIN_DIR):
        os.makedirs(ADMIN_DIR)
        
    while True:
        choice = show_menu()
        if choice == '1':
            add_task()
        elif choice == '2':
            view_queue()
        elif choice == '3':
            reorder_queue()
        elif choice == '4':
            delete_task()
        elif choice == '5':
            pause_and_archive_pipeline()
        elif choice == '6':
            resume_paused_pipeline()
        elif choice == '7':
            print("Exiting...")
            break
        else:
            print("Invalid option.")

if __name__ == '__main__':
    main()
