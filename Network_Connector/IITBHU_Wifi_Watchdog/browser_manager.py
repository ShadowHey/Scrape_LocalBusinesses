from playwright.sync_api import sync_playwright
import pygetwindow as gw
import logging
import time
from config import HEADLESS_MODE

logger = logging.getLogger("wifi_watchdog")

class BrowserManager:
    def __init__(self, profile_dir):
        self.profile_dir = profile_dir
        self.playwright = None
        self.context = None
        
    def start(self):
        if self.context:
            return self.context
            
        logger.debug(f"Starting Playwright browser (Headless: {HEADLESS_MODE})...")
        self.playwright = sync_playwright().start()
        
        args = ["--disable-blink-features=AutomationControlled"]
        if not HEADLESS_MODE:
            args.append("--window-position=0,0")
        else:
            args.append("--headless=new") # Use new headless mode for better extension/profile support
        
        # Use locally installed chrome if possible, otherwise use bundled chromium
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                channel="chrome",
                headless=HEADLESS_MODE,
                args=args
            )
            logger.debug("Dedicated Chrome profile launched successfully.")
        except Exception as e:
            logger.error(f"Failed to launch Chrome with channel='chrome': {e}")
            logger.info("Falling back to bundled Chromium.")
            self.context = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=HEADLESS_MODE,
                args=args
            )
            
        return self.context
        
    def minimize_browser(self):
        if HEADLESS_MODE:
            logger.debug("Running in headless mode, no window to minimize.")
            return
            
        try:
            # Give it a moment to render the title
            time.sleep(1)
            windows = gw.getAllWindows()
            minimized_any = False
            for w in windows:
                title = w.title.lower()
                # IIT(BHU) portal titles or general Chrome titles
                if "chrome" in title or "chromium" in title or "iit" in title or "captive" in title:
                    if not w.isMinimized:
                        w.minimize()
                        logger.debug(f"Minimized window: {w.title}")
                        minimized_any = True
                        
            if not minimized_any:
                logger.debug("Could not find an active Chrome window to minimize.")
        except Exception as e:
            logger.debug(f"Failed to minimize browser window: {e}")
            
    def stop(self):
        if self.context:
            try:
                self.context.close()
            except Exception as e:
                logger.debug(f"Error closing browser context: {e}")
            self.context = None
            
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
            self.playwright = None
            
        logger.debug("Browser manager stopped.")
