import re

with open("c:\\Users\\DhruvBisht\\Desktop\\Firecrawl\\server_pipeline.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Restore the ext_path argument and browser_args for load-extension
old_launch = """def _launch_server_browser(p, profile_path: str):
    \"\"\"
    Launch Chromium using the cloned Golden Profile which already has the
    extension installed from the web store.
    \"\"\"
    from lead import discover_extension, get_extension_service_worker

    user_data_dir = str(Path(profile_path) / "User Data")
    _remove_lock(user_data_dir)

    browser_args = ["""

new_launch = """def _launch_server_browser(p, profile_path: str, ext_path: str):
    \"\"\"
    Launch Chromium with locally loaded extension and auto-accept T&C.
    \"\"\"
    from lead import discover_extension, get_extension_service_worker

    user_data_dir = str(Path(profile_path) / "User Data")
    _remove_lock(user_data_dir)

    browser_args = [
        f"--load-extension={ext_path}",
        f"--disable-extensions-except={ext_path}","""

code = code.replace(old_launch, new_launch)

# 2. Add the storage auto-accept logic right after discover_extension
old_discover = """    extension_id, _ = discover_extension(
        context, "Instant Data Scraper", "ofaokhiedipichpaobibbnahnkdoiiah"
    )
    sw = get_extension_service_worker(context, extension_id)
    maps_page = context.new_page()
    return context, extension_id, sw, maps_page"""

new_discover = """    extension_id, _ = discover_extension(
        context, "Instant Data Scraper", "ofaokhiedipichpaobibbnahnkdoiiah"
    )
    sw = get_extension_service_worker(context, extension_id)
    
    # [CRITICAL FIX] Instantly accept the extension's Terms and Conditions
    # by writing directly to its local storage via the service worker.
    # This bypasses the need for a manually created Windows golden profile!
    try:
        sw.evaluate("chrome.storage.local.set({optIn: true, optInHookShown: true})")
    except Exception as e:
        print(f"      [!] Failed to auto-accept T&C: {e}")

    maps_page = context.new_page()
    return context, extension_id, sw, maps_page"""

code = code.replace(old_discover, new_discover)

# 3. Update the inner calls to _launch_server_browser to pass EXT_PATH
code = re.sub(
    r'context, extension_id, sw, maps_page = _launch_server_browser\(\s*p,\s*profile_path\s*\)',
    r'context, extension_id, sw, maps_page = _launch_server_browser(p, profile_path, EXT_PATH)',
    code
)

with open("c:\\Users\\DhruvBisht\\Desktop\\Firecrawl\\server_pipeline.py", "w", encoding="utf-8") as f:
    f.write(code)
