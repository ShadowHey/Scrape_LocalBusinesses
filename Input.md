# Firecrawl CLI Input Guide

This document provides clear, real-world examples of exactly what the terminal expects you to type or paste when you select options in `main.py` and the `profile_manager`.

## `main.py` Menu Options

### Option 1: Add a New Task
When you select `1` to add a new task, you will be prompted for 4 things:

**1. Search Terms**
You can either type them one by one and type `DONE`, OR you can directly paste a Python list.
*Example (Pasting directly):*
```python
["Public School", "Construction Companies"]
```
*Example (Line-by-line):*
```text
Public School
Construction Companies
DONE
```

**2. Locality Label**
A simple text label used for naming your output folders.
*Example:*
```text
Texas
```

**3. Zip Codes**
You will be asked: `1. Enter manually / Paste list` OR `2. Select from State`.
- **If you choose `1` (Manual)**: You can directly paste a Python set/list, or type line by line.
  *Example (Pasting directly):*
  ```python
  {"75001", "75002", "75006", "75007"}
  ```
  *Example (Line-by-line):*
  ```text
  75001
  75002
  DONE
  ```
- **If you choose `2` (Select from State)**: A numbered list of states from your `final_queue_builder.py` will appear.
  *Example:*
  ```text
  4
  ```

**4. Task Mode**
Select `1` (Emails), `2` (Phones), or `3` (Both).
*Example:*
```text
3
```

---

### Option 3: Reorder Pending Tasks
This allows you to change the execution order of tasks waiting in the queue. You will see a numbered list of tasks. You must provide the new order separated by commas.
*Example (If you have 3 pending tasks and want the 3rd one to run first):*
```text
2, 0, 1
```

---

### Option 4: Cancel / Delete a Task
You will see your queue. You can enter either the **index number** `[0]` or the **Task ID**.
*Example (By Index):*
```text
0
```
*Example (By Task ID):*
```text
a1b2c3d4
```

---

## Option 6: Manage Healthy Profiles (`profile_manager.py`)

When you enter `6` in the main menu, the Profile Manager takes over. It will scan your system and display a menu `[1-7]`.

### Option 2 (Create) or Option 3 (Fix)
The script will open a Chrome window for you to install the extension and log in. Once you are done and have closed the browser, the terminal will wait for you to confirm.
*Example Input expected:*
```text
yes
```

### Option 4 (Delete Unhealthy) or Option 6 (Delete Healthy)
The script will ask you which profile number you want to delete from the printed list.
*Example (Select profile #2 from the list):*
```text
2
```
It will then ask for confirmation to permanently delete the folder.
*Example Input expected:*
```text
y
```

### Option 1: Continue and Save Healthy Profiles
This just saves your profiles to `health_profiles.json` and exits back to the main menu.
*Input expected:*
```text
1
```
*(No further input required).*
