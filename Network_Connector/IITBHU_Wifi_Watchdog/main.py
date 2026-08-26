import time
import argparse
import logging
from config import *
from logger import setup_logger
from connectivity import check_internet, get_current_ssid
from browser_manager import BrowserManager
from portal import perform_login

class WatchdogState:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    AUTHENTICATING = "AUTHENTICATING"
    AUTHENTICATED = "AUTHENTICATED"
    RETRYING = "RETRYING"
    ERROR = "ERROR"

def main():
    parser = argparse.ArgumentParser(description="IIT(BHU) Wi-Fi Watchdog")
    parser.add_argument("--force-login", action="store_true", help="Force login workflow immediately for testing")
    parser.add_argument("--diagnostic", action="store_true", help="Enable verbose diagnostic logging")
    args = parser.parse_args()
    
    logger = setup_logger(args.diagnostic)
    logger.info("Watchdog started")
    
    if not IITBHU_USERNAME or not IITBHU_PASSWORD:
        logger.error("Credentials not found! Please set IITBHU_USERNAME and IITBHU_PASSWORD in .env")
        if not args.force_login:
            return

    browser_manager = BrowserManager(CHROME_PROFILE_DIR)
    state = WatchdogState.ONLINE
    offline_count = 0
    login_retries = 0
    
    def verify_internet_and_update_state():
        nonlocal state, offline_count
        if check_internet(TEST_URLS):
            if state != WatchdogState.ONLINE:
                logger.info("Internet status: ONLINE")
            state = WatchdogState.ONLINE
            offline_count = 0
            return True
        else:
            if state != WatchdogState.OFFLINE:
                logger.info("Internet status: OFFLINE")
            return False

    def handle_authentication():
        nonlocal login_retries
        logger.info("Starting captive portal authentication")
        logger.info("Launching dedicated Chrome")
        
        try:
            context = browser_manager.start()
            
            # Pass the entire browser context to the portal logic so it can scan all tabs
            success = perform_login(context, IITBHU_USERNAME, IITBHU_PASSWORD)
            
            if not success:
                logger.warning("Portal login execution reported issues, but will verify connectivity regardless.")
                
            # Allow time for backend to authorize MAC address
            time.sleep(3)
                
        except Exception as e:
            logger.error(f"Error during authentication workflow: {e}")
            
        # Verify Internet after attempt
        if check_internet(TEST_URLS):
            logger.info("Internet verification successful")
            logger.info("Authentication successful")
            login_retries = 0
            if KEEP_BROWSER_OPEN:
                logger.info("Chrome minimized")
                browser_manager.minimize_browser()
            else:
                browser_manager.stop()
            logger.info("Returning to monitoring")
            return True
        else:
            logger.warning("Internet verification failed after authentication attempt")
            login_retries += 1
            if login_retries >= MAX_LOGIN_RETRIES:
                logger.error("Max login retries reached. Will wait before trying again.")
                if not KEEP_BROWSER_OPEN:
                    browser_manager.stop()
                return False
            return False

    if args.force_login:
        logger.info("Force login requested")
        handle_authentication()
        if not KEEP_BROWSER_OPEN:
            browser_manager.stop()
        logger.info("Force login complete. Exiting...")
        return
            
    while True:
        try:
            # Check SSID before doing any network requests
            current_ssid = get_current_ssid()
            if current_ssid and current_ssid not in TARGET_WIFI_NETWORKS:
                if state != "IDLE_WRONG_WIFI":
                    logger.info(f"Connected to '{current_ssid}'. Waiting for target network: {TARGET_WIFI_NETWORKS}.")
                    state = "IDLE_WRONG_WIFI"
                    
                # We optionally close the browser if we switch to a different network to save RAM
                if browser_manager.context:
                    logger.debug("Stopping browser to save RAM on non-target network.")
                    browser_manager.stop()
                    
                time.sleep(CHECK_INTERVAL)
                continue
            
            # If we were idle, reset to online when target network connects
            if state == "IDLE_WRONG_WIFI":
                logger.info(f"Target network '{current_ssid}' detected. Resuming monitoring.")
                state = WatchdogState.ONLINE
                offline_count = 0

            if state == WatchdogState.ONLINE or state == WatchdogState.OFFLINE:
                is_online = verify_internet_and_update_state()
                
                if not is_online:
                    state = WatchdogState.OFFLINE
                    offline_count += 1
                    logger.debug(f"Offline condition check: {offline_count}/{FAILURE_CONFIRMATION_COUNT}")
                    
                    if offline_count >= FAILURE_CONFIRMATION_COUNT:
                        logger.info("Offline condition confirmed")
                        state = WatchdogState.AUTHENTICATING
                        offline_count = 0
                else:
                    # We are online, nothing to do
                    pass
                    
            elif state == WatchdogState.AUTHENTICATING:
                success = handle_authentication()
                if success:
                    state = WatchdogState.ONLINE
                else:
                    state = WatchdogState.RETRYING
                    
            elif state == WatchdogState.RETRYING:
                if login_retries >= MAX_LOGIN_RETRIES:
                    logger.info(f"Sleeping for {CHECK_INTERVAL * 2}s before resetting retry count.")
                    time.sleep(CHECK_INTERVAL * 2)
                    login_retries = 0
                    state = WatchdogState.OFFLINE
                else:
                    logger.info("Retrying authentication...")
                    state = WatchdogState.AUTHENTICATING
                    
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Watchdog stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(CHECK_INTERVAL)
            
    # Cleanup on exit
    browser_manager.stop()

if __name__ == "__main__":
    main()
