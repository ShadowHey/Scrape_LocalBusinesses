import socket
import time

def is_internet_available(host="8.8.8.8", port=53, timeout=3):
    """
    Check if the internet is available by attempting a socket connection
    to Google DNS (8.8.8.8) on port 53.
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def wait_for_network(poll_interval=10):
    """
    Blocks and waits if the network is down, checking every `poll_interval` seconds.
    """
    if is_internet_available():
        return

    print("\n[⚠️] Network disconnected. Waiting for connection to restore...", flush=True)
    while not is_internet_available():
        time.sleep(poll_interval)
    
    print("[✅] Network restored! Resuming operations.\n", flush=True)

def handle_captive_portal(context):
    """
    Automates the captive portal login for IIT(BHU) network (192.168.249.1)
    using the provided Playwright context.
    """
    if is_internet_available():
        return True

    print("\n[⚠️] Network disconnected. Attempting captive portal login...", flush=True)
    try:
        portal_page = context.new_page()
        # Navigate directly to the captive portal IP
        portal_page.goto("http://192.168.249.1", timeout=15000)
        
        # Fill in credentials using generic selectors
        portal_page.fill('input[name="username"], input[type="text"]', "23114009", timeout=5000)
        portal_page.fill('input[name="password"], input[type="password"]', "dhrunita@54", timeout=5000)
        
        # Click Continue/Submit
        portal_page.click('button:has-text("Continue"), input[type="submit"]', timeout=5000)
        
        # Wait a bit for the connection to establish
        portal_page.wait_for_timeout(3000)
        portal_page.close()
        
        # Re-check internet
        if is_internet_available():
            print("[✅] Network restored via captive portal! Resuming operations.\n", flush=True)
            return True
        else:
            print("[❌] Captive portal login failed. Waiting manually...\n", flush=True)
            
    except Exception as e:
        print(f"[❌] Captive portal automation failed: {e}\nWaiting manually...", flush=True)
        try:
            portal_page.close()
        except:
            pass

    # Fallback to the old waiting logic if automation fails
    wait_for_network()
    return True

def wait_for_network_with_portal(context, poll_interval=10):
    if is_internet_available():
        return
    handle_captive_portal(context)
