# Example Task Walkthrough

This guide will walk you through setting up and running your first task from scratch. We recommend opening a **split terminal** in your editor so you can see all three of these scripts running side-by-side.

## Step 1: Set Up Chrome Profiles
Before scraping, we need to make sure we have authenticated Chrome profiles ready to avoid being blocked.

1. Open your terminal and run:
   ```bash
   python scraper_core/profile_manager.py
   ```
2. The script will ask you how many profiles you want to create or verify for this session. Enter the number of profiles you need (e.g., `10`).
3. It will launch browser windows to initialize these profiles. Follow any on-screen prompts if required. Once finished, it will save the profiles to `admin/health_profiles.json`.

## Step 2: Add a Task via Main Menu
Next, we'll queue up our actual scraping task.

1. In a split terminal window, run:
   ```bash
   python main.py
   ```
2. The interactive menu will appear. Type `1` and press Enter to select **Add a New Task**.
3. **Search Terms**: It will prompt you for search terms. You can enter them line by line. Type `DONE` when finished.
   ```text
   Corporate Office
   Logistics Company
   DONE
   ```
4. **Locality Label**: Enter a descriptive name for this batch.
   ```text
   Chicago North IL
   ```
5. **Zip Codes**: Enter `1` to paste manually, or `2` to pick from the built-in states list. If you choose `1`, type them line by line and hit `DONE`.
   ```text
   60601
   60602
   DONE
   ```
6. **Task Mode**: Select what you want to scrape. Press `3` for Both (Emails + Phones).

The task is now saved in the `admin/tasks.json` queue as `pending`!

## Step 3: Start the Pipeline Executor
Now that the task is queued and profiles are ready, it's time to start the engine.

1. In another split terminal pane, run:
   ```bash
   python pipeline_executor.py
   ```
2. The executor will automatically detect the pending task you just added.
3. It will first run `lead.py` to scrape Google Maps using the profiles you generated.
4. Next, it will run `aggregate.py` to clean and combine the results.
5. Finally, it will run the email scrapers (`pipeline.py`) and phone scrapers (`find_phone.py`).

You can watch the progress in real-time. If you ever need to stop, simply go back to your `main.py` terminal and select **Option 8 (Pause Pipeline and Archive)**!
