import json
import os
import time
import subprocess
import shutil

BASE_DIR = r"C:\Users\DhruvBisht\Desktop\Firecrawl"
ADMIN_DIR = os.path.join(BASE_DIR, 'admin')
TASKS_JSON = os.path.join(ADMIN_DIR, 'tasks.json')
STOP_FLAG = os.path.join(ADMIN_DIR, 'STOP_FLAG')
PAUSE_FLAG = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')

print("=== Setting up test tasks ===")
import test_plan
test_plan.create_tasks()

print("\n=== Starting pipeline_executor.py ===")
executor_process = subprocess.Popen(
    ["python", "pipeline_executor.py"], 
    cwd=BASE_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Wait 15 seconds to let lead.py start up and run a bit
time.sleep(15)

print("\n=== Pausing the Pipeline (Simulating Option 4) ===")
# 1. Write STOP_FLAG and PIPELINE_PAUSED
with open(STOP_FLAG, 'w') as f:
    f.write("STOP")
with open(PAUSE_FLAG, 'w') as f:
    f.write("PAUSED")

# 2. Move Task 1 to end
with open(TASKS_JSON, 'r') as f:
    tasks = json.load(f)
t = tasks.pop(0)
t['status'] = 'paused'
tasks.append(t)
with open(TASKS_JSON, 'w') as f:
    json.dump(tasks, f, indent=4)

print("Task 1 moved to end. Waiting 10 seconds for executor to handle pause and archive...")
time.sleep(10)

print("\n=== Verifying Archiving ===")
logs_dir = os.path.join(BASE_DIR, 'Logs_NewRuns')
found_archive = False
if os.path.exists(logs_dir):
    for item in os.listdir(logs_dir):
        if "task_1_both" in item and "PAUSED" in item:
            print(f"[+] Verified: Found paused archive folder '{item}' in Logs_NewRuns.")
            found_archive = True
if not found_archive:
    print("[-] Failed: Could not find archived task 1 folder.")

print("\n=== Reordering Queue (Simulating Option 3) ===")
# Currently tasks are: Task 2, Task 3, Task 1 (paused).
# Task 2 is already at the front now! Let's just make sure.
with open(TASKS_JSON, 'r') as f:
    tasks = json.load(f)
print(f"Queue order: {[t['id'] for t in tasks]}")

print("\n=== Resuming Pipeline (Simulating Option 5) ===")
if os.path.exists(PAUSE_FLAG):
    os.remove(PAUSE_FLAG)
    print("PIPELINE_PAUSED flag removed. Waiting 10 seconds for executor to pick up Task 2...")
    
time.sleep(10)

# Kill executor
print("\n=== Terminating executor ===")
executor_process.terminate()
try:
    executor_process.wait(timeout=3)
except:
    executor_process.kill()

print("\n=== Executor Output ===")
output = executor_process.communicate()[0]
print(output)
