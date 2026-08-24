# Refactor `profile_manager.py` to "Wipe and Recreate" Workflow

The goal is to modify `profile_manager.py` to drop the failing "health check" loop and instead adopt a simpler workflow that wipes old profiles and creates brand new ones automatically.

## User Review Required
> [!IMPORTANT]
> - **Selective Process Killing:** We will only kill `chrome.exe` processes that were launched with `--user-data-dir=.../ChromeUserData*`. Your personal Chrome browser windows will remain unaffected.
> - **No Background Monitoring Loop:** The script will no longer stay open for 20-minute intervals. It will create the profiles, save them to the JSON file, and exit completely, leaving the work to `pipeline_executor.py`.

## Proposed Changes

---

### Profile Manager

#### [MODIFY] [profile_manager.py](file:///c:/Users/DhruvBisht/Desktop/Firecrawl/scraper_core/profile_manager.py)

1. **Selective Nuke Logic (New Function):**
   - Add a function `kill_scraper_browsers()` that uses Windows commands (`wmic process get processid,commandline`) to find all `chrome.exe` processes.
   - It will check if `ChromeUserData` is in the command line arguments. If it is, it kills that specific Process ID (PID).
   - This ensures we don't accidentally close your personal browsing sessions.

2. **Folder Cleanup (New Logic in `main()`):**
   - After running `kill_scraper_browsers()`, the script will use `shutil.rmtree()` to safely delete all existing `ChromeUserData*` folders in the base directory.

3. **Creation Loop Refactor:**
   - Ask the user for the number of desired profiles (N).
   - Loop from `1` to `N` and create `ChromeUserData1`, `ChromeUserData2`, etc.
   
4. **Extension Setup Automation Update:**
   - Retain the `ctypes` simulation (Left Arrow + Enter) to accept the native Chrome popup.
   - Update Playwright logic to wait for the extension's welcome page.
   - Use Playwright locators to find and click the **"Choose all"** button, followed by the **"Confirm and continue"** button, instead of the generic "agree" button.
   - Close the browser tab once completed.

5. **Handoff and Exit:**
   - Once all `N` profiles are successfully set up, write their absolute paths to `admin/health_profiles.json`.
   - Remove the `while True:` continuous monitoring loop at the end of the file.
   - Exit the script gracefully.

## Verification Plan

### Manual Verification
1. Run `python scraper_core/profile_manager.py`.
2. Input `2` profiles to test.
3. Verify that only the automation Chrome windows close, while any personal Chrome windows stay open.
4. Verify that the extension is successfully added, "Choose all" and "Confirm and continue" are clicked automatically.
5. Verify that `admin/health_profiles.json` contains exactly 2 profile paths, and the script exits instead of waiting 20 minutes.
