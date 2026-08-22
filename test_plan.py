import json
import os
import time
import uuid

ADMIN_DIR = r"C:\Users\DhruvBisht\Desktop\Firecrawl\admin"
TASKS_JSON = os.path.join(ADMIN_DIR, 'tasks.json')

def create_tasks():
    tasks = []
    
    # Task 1: Both
    tasks.append({
        "id": "task_1_both",
        "created_at": "2026-08-16T00:00:00",
        "search_terms": ["Plumber", "Electrician"],
        "locality": "Austin",
        "zip_codes": ["73301", "73344", "78701", "78702"],
        "mode": "both",
        "status": "pending",
        "progress": {"completed_zips": [], "current_step": "init"}
    })
    
    # Task 2: Emails
    tasks.append({
        "id": "task_2_emails",
        "created_at": "2026-08-16T00:01:00",
        "search_terms": ["Software"],
        "locality": "Seattle",
        "zip_codes": ["98101"],
        "mode": "emails",
        "status": "pending",
        "progress": {"completed_zips": [], "current_step": "init"}
    })
    
    # Task 3: Phones
    tasks.append({
        "id": "task_3_phones",
        "created_at": "2026-08-16T00:02:00",
        "search_terms": ["Restaurant"],
        "locality": "NewYork",
        "zip_codes": ["10001"],
        "mode": "phones",
        "status": "pending",
        "progress": {"completed_zips": [], "current_step": "init"}
    })
    
    if not os.path.exists(ADMIN_DIR):
        os.makedirs(ADMIN_DIR)
        
    with open(TASKS_JSON, 'w') as f:
        json.dump(tasks, f, indent=4)
        
    print("Test tasks created.")

if __name__ == '__main__':
    create_tasks()
