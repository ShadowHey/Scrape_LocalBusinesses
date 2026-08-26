import logging
import re
import time

logger = logging.getLogger("wifi_watchdog")

def scan_tabs_for_keywords(context, keywords):
    """
    Scans all visible pages in the context for specific keywords in their innerText.
    Returns the page object if found, otherwise None.
    """
    # Wait briefly in case a new tab is still initializing
    time.sleep(2)
    
    for page in context.pages:
        # Skip extension background pages
        if page.url.startswith("chrome-extension://"):
            continue
            
        try:
            # Wait a little bit for the DOM to be ready
            page.wait_for_load_state("domcontentloaded", timeout=3000)
            content = page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''")
            
            for keyword in keywords:
                if keyword.lower() in content:
                    logger.debug(f"Found keyword '{keyword}' in tab: {page.url}")
                    return page
        except Exception as e:
            logger.debug(f"Error scanning tab {page.url}: {e}")
            continue
            
    return None

def perform_login(context, username, password):
    logger.info("Attempting captive portal intercept workflow...")
    
    # 1. Trigger the intercept by navigating to a plain HTTP site
    trigger_url = "http://neverssl.com/"
    logger.debug(f"Navigating to {trigger_url} to trigger intercept.")
    
    # Get or create a working page
    visible_pages = [p for p in context.pages if not p.url.startswith("chrome-extension://")]
    page = visible_pages[-1] if visible_pages else context.new_page()
    
    try:
        page.bring_to_front()
        # Navigate without waiting for full load, as the intercept might disrupt it
        page.goto(trigger_url, timeout=15000, wait_until="commit")
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception as e:
        logger.debug(f"Navigation to trigger URL hit an exception (often normal for intercepts): {e}")

    # Give the network time to redirect us
    time.sleep(3)

    # 2. Check if we are already authenticated by scanning for the success page keywords
    success_keywords = ["terms & disclaimer agreement", "leave it open in the background", "logout"]
    if scan_tabs_for_keywords(context, success_keywords):
        logger.info("Portal appears to already be authenticated.")
        return True

    # 3. Look for the firewall intercept page (Fortinet/FortiGate usually says 'continue' or 'firewall')
    logger.debug("Scanning tabs for firewall intercept page...")
    intercept_keywords = ["continue to credential", "firewall authentication", "fortigate", "continue to the authentication", "click continue"]
    
    intercept_page = scan_tabs_for_keywords(context, intercept_keywords)
    
    if intercept_page:
        logger.info("Firewall intercept page detected. Clicking continue...")
        intercept_page.bring_to_front()
        try:
            # Try to find a continue button
            continue_btn = intercept_page.locator("button, input[type='submit'], a, input[type='button']").filter(
                has_text=re.compile("continue", re.IGNORECASE)
            ).first
            
            if continue_btn.count() > 0:
                continue_btn.click()
            else:
                logger.warning("Could not find a 'Continue' button on the intercept page. Clicking any submit...")
                intercept_page.locator("input[type='submit'], button[type='submit']").first.click()
                
            logger.debug("Clicked continue on intercept page. Waiting for redirect/new tab...")
            time.sleep(5) # Crucial wait for the new tab to spawn or redirect to happen
        except Exception as e:
            logger.error(f"Error interacting with intercept page: {e}")
    else:
        logger.debug("No firewall intercept page detected. Proceeding directly to look for the login portal.")

    # 4. Look for the actual login portal page
    logger.debug("Scanning tabs for the authentication login portal...")
    login_keywords = ["authentication required", "username"]
    login_page = scan_tabs_for_keywords(context, login_keywords)

    if not login_page:
        logger.warning("Could not find the login portal across any open tabs.")
        return False

    logger.info("Login portal detected. Submitting credentials...")
    login_page.bring_to_front()
    
    try:
        # Wait for username input
        user_input = login_page.locator("input[name*='user'], input[type='text'], input#username").first
        user_input.wait_for(state="visible", timeout=5000)
        user_input.fill(username)
        
        # Wait for password input
        pass_input = login_page.locator("input[name*='pass'], input[type='password'], input#password").first
        pass_input.wait_for(state="visible", timeout=5000)
        pass_input.fill(password)
        
        logger.debug("Credentials entered.")
        
        # Click Continue/Login button
        submit_btn = login_page.locator("button, input[type='submit'], input[type='button']").filter(
            has_text=re.compile("continue|login|submit|sign in", re.IGNORECASE)
        ).first
        
        if submit_btn.count() > 0:
            submit_btn.click()
        else:
            login_page.locator("input[type='submit'], button[type='submit']").first.click()
            
        logger.debug("Clicked submit button. Waiting for authentication to process...")
        
        # 5. Wait for the success markers to appear on this page
        try:
            login_page.wait_for_function(
                "() => document.body && (document.body.innerText.toLowerCase().includes('logout') || "
                "document.body.innerText.toLowerCase().includes('terms & disclaimer agreement') || "
                "document.body.innerText.toLowerCase().includes('keep your authentication session active'))",
                timeout=15000
            )
            logger.info("Authentication success page detected.")
            return True
        except Exception as e:
            logger.warning(f"Did not detect successful authentication markers on this tab: {e}")
            # Could be it spawned yet another tab, or it's just slow. Let the internet connectivity check decide.
            return True
            
    except Exception as e:
        logger.error(f"Login process failed on the portal tab: {e}")
        return False
