import json
import os
import shutil

admin_dir = 'admin'
tasks_file = os.path.join(admin_dir, 'tasks.json')
history_file = os.path.join(admin_dir, 'history.json')

# 1. Reset tasks.json
if os.path.exists(tasks_file):
    with open(tasks_file, 'r') as f:
        tasks = json.load(f)
    if not isinstance(tasks, list):
        tasks = [tasks]
    for t in tasks:
        if 'test_task' in t.get('id', ''):
            t['status'] = 'pending'
            # Give it a fresh ID so history doesn't interfere
            if not t['id'].endswith('_v2'):
                t['id'] = t['id'] + '_v2'
    with open(tasks_file, 'w') as f:
        json.dump(tasks, f, indent=4)

# 2. Clear temp directories so it starts totally fresh
for d in ['temp_csvs', 'final_results', 'pre_segment_csvs', 'uploadable_csvs']:
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)

print('Task reset successfully. Fresh IDs assigned and temp directories cleared.')
