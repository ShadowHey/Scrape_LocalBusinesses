import json
import os

ADMIN_DIR = r"C:\Users\DhruvBisht\Desktop\Firecrawl\admin"
TASKS_JSON = os.path.join(ADMIN_DIR, 'tasks.json')
STOP_FLAG = os.path.join(ADMIN_DIR, 'STOP_FLAG')
PAUSE_FLAG = os.path.join(ADMIN_DIR, 'PIPELINE_PAUSED')

# 1. Stop executor gracefully
with open(STOP_FLAG, 'w') as f:
    f.write("STOP")
with open(PAUSE_FLAG, 'w') as f:
    f.write("PAUSED")

# 2. Repair the task
if os.path.exists(TASKS_JSON):
    with open(TASKS_JSON, 'r') as f:
        tasks = json.load(f)
        
    for task in tasks:
        if task['id'] == 'c3929b27':
            print("Repairing task c3929b27...")
            # Clean up the search terms list
            raw_terms = task['search_terms']
            cleaned = []
            for item in raw_terms:
                c = item.strip().strip(',').strip('"').strip("'")
                if c and c not in ['[', ']', '{', '}']:
                    cleaned.append(c)
            task['search_terms'] = cleaned
            task['status'] = 'pending'
            
    with open(TASKS_JSON, 'w') as f:
        json.dump(tasks, f, indent=4)
        print("Task repaired successfully.")
