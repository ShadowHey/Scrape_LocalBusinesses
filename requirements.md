# Project Requirements

This repository requires specific Python libraries and a defined file structure to function properly. 

## Python Libraries
You can install the necessary dependencies using pip. Ensure you have Python 3.8 or newer installed.

```bash
pip install pandas playwright beautifulsoup4 requests
playwright install chromium
```

- **pandas**: Used heavily for reading, writing, and aggregating the CSV files during the scraping pipeline.
- **playwright**: The core automation library used to drive the Chromium browsers for Google Maps and Phone scraping.
- **beautifulsoup4 & requests**: Used by the email scraper module to parse HTML and extract data quickly from target websites.

## Important Directories & Files
- **`main.py`**: The interactive task scheduler and queue manager.
- **`pipeline_executor.py`**: The background worker that reads the queue and executes the scraping scripts.
- **`scraper_core/profile_manager.py`**: The utility for creating and managing authenticated Chrome profiles to avoid bot detection.
- **`admin/` directory**: Automatically created by `main.py` to store state files like `tasks.json`, `history.json`, and pause flags.
- **`Logs_NewRuns/` directory**: Automatically created by `file_manager.py` to archive output files securely after tasks complete, error out, or are paused.
