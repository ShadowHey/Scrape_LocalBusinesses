# Firecrawl Pipeline Manager

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

The pipeline operates using three primary files. It's recommended to run them in a **split terminal** (as shown in your setup) so you can monitor profiles, queue status, and executor logs simultaneously in one window.

### 1. `scraper_core/profile_manager.py`
**What it does:** This script manages authenticated Google Chrome profiles for the Playwright bots. Using established profiles helps prevent captchas and bans from Google.
**How to use:**
Before starting any tasks, run this script to generate or verify the Chrome profiles. It will automatically walk you through setting them up.
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
- **`cancel_task()` (Option 4):** Lets you completely delete a task from the queue.
- **`resume_pipeline()` (Option 5):** A legacy option to manually clear a stuck pipeline.
- **`pause_and_archive_pipeline()` (Option 8):** Globally pauses the pipeline and instructs the executor to stop the current task, archive its files safely into `Logs_NewRuns`, and shut down.
- **`resume_paused_pipeline()` (Option 9):** Unpauses the pipeline globally, allowing you to restart the executor to pick up a paused task exactly where it left off, automatically restoring its files.

### 3. `pipeline_executor.py`
**What it does:** The engine of the project. It constantly watches the queue for `pending` or `paused` tasks and executes them sequentially. It handles restoring paused files, executing the Map scraper, aggregator, and then the email/phone scrapers based on the task mode.
**How to use:**
Once your profiles are ready and tasks are added via `main.py`, run this in a separate split terminal:
```bash
python pipeline_executor.py
```

## Running an Example Task
Please check `example_task.md` for a step-by-step walkthrough of starting and running your first task!
