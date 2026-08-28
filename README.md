# Firecrawl Pipeline Manager

## 🚀 Latest Version Updates
This update introduces robust auto-recovery and repository cleanup:
- **Auto-Resume Interrupted Tasks**: `pipeline_executor.py` has been upgraded to automatically detect and resume tasks that were abruptly interrupted (e.g., due to a sudden power cut). It intelligently scans your working directory to validate completed pipeline stages, updates its history, and seamlessly picks up exactly where it left off without any manual intervention.
- **Repository Cleanup**: The `IITBHU_Wifi_Watchdog` module has been completely untracked from Git and added to `.gitignore`, preventing unnecessary bloat in the repository while keeping your local files safe.

---

Welcome to the Firecrawl Pipeline Manager! This tool automates the process of finding local business leads via Google Maps, scraping their websites for emails, and extracting their phone numbers.

## How to Set Up the Project on Your Computer

1. **Install Python**: Ensure you have Python 3.8+ installed on your system.
2. **Clone the Repository**: Download or clone this repository to your local machine.
3. **Install Requirements**: Install the required Python libraries. You can refer to `requirements.md` for a complete list. Run the following command in your terminal:
   ```bash
   pip install pandas playwright beautifulsoup4 requests
   ```
4. **Install Playwright Browsers**: After installing the Python packages, you must install the Playwright browser binaries:
   ```bash
   playwright install chromium
   ```

## Setting Up Important Files

The pipeline operates using these primary files. It's recommended to run them in a **split terminal** (as shown in your setup) so you can monitor profiles, queue status, and executor logs simultaneously.

### 1. `scraper_core/profile_manager.py`
**What it does:** This script manages authenticated Google Chrome profiles for the Playwright bots. Using established profiles helps prevent captchas and bans from Google.
**How to use:**
Before starting any tasks, run this script manually *one time* to generate or verify the Chrome profiles and set your **Safety Limit**. It will automatically walk you through setting them up.
```bash
python scraper_core/profile_manager.py
```

### 2. `main.py`
**What it does:** This is the interactive Task Scheduler & Pipeline Manager. It handles the queue, lets you add new tasks, pause running tasks, or reorder pending ones.
**How to use:**
Run it in an interactive terminal. 
```bash
python main.py
```
**Functions inside `main.py`:**
- **`add_task()` (Option 1):** Walks you through adding a new search term (e.g., "Corporate Office"), Locality, Zip codes, and scraping mode (Emails, Phones, or Both). It saves the task to the queue with a `pending` status.
- **`view_queue()` (Option 2):** Lists all current tasks, their modes, and statuses (`pending`, `running`, `paused`, `completed`).
- **`reorder_queue()` (Option 3):** Lets you change the priority of pending tasks by inputting a new comma-separated order.
- **`delete_task()` (Option 4):** Lets you completely delete a task from the queue.
- **`pause_and_archive_pipeline()` (Option 5):** Globally pauses the pipeline and instructs the executor to stop the current task, archive its files safely into `Logs_NewRuns`, and shut down.
- **`resume_paused_pipeline()` (Option 6):** Unpauses the pipeline globally, allowing you to restart the executor to pick up a paused task exactly where it left off, automatically restoring its files.

### 3. `pipeline_executor.py`
**What it does:** The engine of the project. It constantly watches the queue for `pending` or `paused` tasks and executes them sequentially. It handles restoring paused files, executing the Map scraper, aggregator, and then the email/phone scrapers based on the task mode.
**How to use:**
Once your profiles are ready and tasks are added via `main.py`, run this in a separate split terminal:
```bash
python pipeline_executor.py
```

### 4. `automator.py`
**What it does:** A background watchdog that monitors your executor for Profile Shortages. If the pipeline burns too many profiles and dips below your Safety Limit, the executor will pause itself and signal this script. `automator.py` will run `profile_manager.py` automatically in silent mode, build fresh profiles, and instantly wake the executor back up to continue scraping without any manual intervention.
**How to use:**
Run this in its own separate terminal and let it sit silently:
```bash
python automator.py
```

## Recommendations

### Handling Chrome Profile Corruption (6-Hour Refresh Cycle)
Over long scraping sessions, Chrome profiles can sometimes become corrupted, consume excessive memory, or fail to display the Instant Data Scraper properly. To ensure the highest success rate and prevent these issues, we recommend the following **6-Hour Refresh Cycle**:

1. **Pause Pipeline and Archive (`main.py` -> Option 5):** In the middle of a long pipeline (e.g., after 6 hours), select option 5 in `main.py`. This safely halts the current task, archives all progress without data loss, marks the task as paused, and gracefully shuts down the executor.
2. **Recreate Profiles:** Run `python scraper_core/profile_manager.py`. This will automatically kill any stuck browser processes, wipe the corrupted `ChromeUserData` folders, and provision fresh profiles with the extension set up.
3. **Resume Pipeline (`main.py` -> Option 6):** Select option 6 to unpause the system.
4. **Restart Executor:** Run `python pipeline_executor.py`. The executor will detect the paused task, restore its archive, skip already completed stages via `history.json`, and seamlessly resume the scrape with the new profiles.

## Running an Example Task
Please check `example_task.md` for a step-by-step walkthrough of starting and running your first task!
