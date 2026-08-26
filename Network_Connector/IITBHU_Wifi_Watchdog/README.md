# IIT(BHU) Wi-Fi Watchdog

An automated, robust background worker that continuously monitors internet connectivity and automatically authenticates through the IIT(BHU) captive portal (192.168.249.1) whenever required.

It creates a dedicated Chrome profile, authenticates securely without requiring manual input, verifies successful internet restoration, minimizes the browser to maintain the active session, and falls back to a low-resource monitoring loop.

## 1. Prerequisites

- Windows 10/11
- Python 3.11+
- Google Chrome installed locally

## 2. Installation

Open PowerShell or Command Prompt, and run these exact commands:

1. **Create and activate a virtual environment:**
   ```powershell
   cd c:\Users\DhruvBisht\Desktop\Network_Connector\IITBHU_Wifi_Watchdog
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install Python dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```powershell
   python -m playwright install
   ```

## 3. Configuration

1. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```

2. Open `.env` and configure your credentials:
   ```env
   IITBHU_USERNAME=23114009
   IITBHU_PASSWORD=your_actual_password_here
   ```
   *(Note: The `.env` file is ignored by Git. Your credentials will remain secure and will never be logged.)*

## 4. Usage & Testing

### Test 1 — Force Authentication
Run this command to test the login workflow immediately without waiting for the internet to disconnect.
```powershell
python main.py --force-login
```
**Expected:** 
1. A dedicated Chrome profile launches.
2. The IIT(BHU) captive portal opens.
3. Username and Password are automatically entered.
4. "Continue" is clicked.
5. Success page is detected and actual internet connectivity is verified.
6. The Chrome window is minimized, and the script exits.

### Test 2 — Normal Watchdog
Run this command to start the continuous background monitor.
```powershell
python main.py
```
**Expected:**
- If internet is active, it runs lightweight HTTP checks every 20 seconds.
- If internet disconnects, it confirms the failure, launches/reuses Chrome, authenticates, minimizes Chrome, and resumes monitoring.
- It consumes very little CPU as it spends most of its time sleeping.

### Diagnostic Mode
To see detailed logs including network checks and DOM parsing steps:
```powershell
python main.py --diagnostic
```

## 5. Architecture Explanation

- **`main.py`**: A robust State Machine (`ONLINE` -> `OFFLINE` -> `AUTHENTICATING` -> `ONLINE`). Sleeps mostly, avoiding busy loops.
- **`connectivity.py`**: Uses `httpx` to perform lightweight, non-blocking requests to `generate_204` endpoints. Checks actual internet routing, not just Wi-Fi connection.
- **`portal.py`**: Uses Playwright's DOM-based locators (`page.locator()`). Highly resilient against layout changes; it dynamically identifies fields and buttons using CSS attributes and inner text, completely avoiding screen coordinates. 
- **`browser_manager.py`**: Maintains a dedicated Chrome profile (`chrome_profile/`) via Playwright's persistent context. Minimizes the window on Windows using `pygetwindow` since the IIT(BHU) portal explicitly requires keeping the window open for session validity.
- **`logger.py`**: Manages rolling logs in `logs/wifi_watchdog.log`.

## 6. Background Execution on Windows

To run the script completely in the background without a command prompt window, use `pythonw.exe`:
```powershell
pythonw.exe main.py
```
You can check `logs/wifi_watchdog.log` to see what it's doing.

To stop it, you will need to open Task Manager and end the `pythonw.exe` process.

*(You can later place a shortcut to a `.bat` file running this command in `shell:startup` to run it automatically when Windows starts.)*

## 7. Troubleshooting

- **Login Fails:** Check `logs/wifi_watchdog.log`. Ensure the `.env` credentials are correct. Use `--diagnostic` to see detailed failure steps.
- **Chrome Fails to Launch:** Ensure Google Chrome is installed. The tool attempts to use local Chrome via `channel="chrome"` but falls back to Playwright's bundled Chromium if needed.
- **Multiple Chrome Windows:** The watchdog reuses the existing persistent context. Do not manually close the minimized Chrome window, as the captive portal requires it to remain open to keep the session alive.
