import os

filepath = r"C:\Users\DhruvBisht\Desktop\Firecrawl\pipeline_executor.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Update run_executor to check PIPELINE_PAUSED
old_loop_start = """def run_executor():
    print("Task Executor started. Waiting for pending tasks...")
    while True:
        tasks = load_tasks()"""

new_loop_start = """def is_pipeline_paused():
    pause_flag = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')
    return os.path.exists(pause_flag)

def run_executor():
    print("Task Executor started. Waiting for pending tasks...")
    while True:
        if is_pipeline_paused():
            time.sleep(2)
            continue
            
        tasks = load_tasks()"""

content = content.replace(old_loop_start, new_loop_start)

# 2. Call restore_task when a pending task is picked up
old_pick_task = """        print(f"\\n[*] Found pending task: {pending_task['id']}")
        
        # Mark as running"""

new_pick_task = """        print(f"\\n[*] Found pending task: {pending_task['id']}")
        
        import file_manager
        file_manager.restore_task(pending_task)
        
        # Mark as running"""

content = content.replace(old_pick_task, new_pick_task)

# 3. Call archive_task(is_paused=True) on cancellation
old_cancel_block = """            else:
                if was_cancelled:
                    # Make sure it's marked as paused if it wasn't already by main.py
                    tasks[current_idx]['status'] = 'paused'
                elif tasks[current_idx]['status'] == 'running':
                    tasks[current_idx]['status'] = 'error'"""

new_cancel_block = """            else:
                if was_cancelled:
                    # Make sure it's marked as paused if it wasn't already by main.py
                    if current_idx != -1:
                        tasks[current_idx]['status'] = 'paused'
                    import file_manager
                    file_manager.archive_task(pending_task, is_paused=True)
                elif current_idx != -1 and tasks[current_idx]['status'] == 'running':
                    tasks[current_idx]['status'] = 'error'"""

content = content.replace(old_cancel_block, new_cancel_block)

with open(filepath, "w") as f:
    f.write(content)

print("executor patched successfully")
