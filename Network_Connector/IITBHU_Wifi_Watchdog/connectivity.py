import httpx
import logging
import subprocess

logger = logging.getLogger("wifi_watchdog")

def get_current_ssid():
    """
    Returns the SSID of the currently connected Wi-Fi network on Windows.
    Returns None if not connected or if an error occurs.
    """
    try:
        # Run netsh wlan show interfaces
        result = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in result.split("\n"):
            if " SSID " in line:
                # The line format is usually: "    SSID                   : NetworkName"
                return line.split(":")[1].strip()
    except Exception as e:
        logger.debug(f"Failed to check Wi-Fi SSID: {e}")
    return None

def check_internet(test_urls):
    """
    Check internet connectivity by hitting captive portal detection endpoints.
    Returns True if internet is available, False otherwise.
    """
    for url in test_urls:
        try:
            # Short timeout to avoid blocking
            with httpx.Client(timeout=3.0) as client:
                response = client.get(url)
                # If we get a 204 No Content, we have direct internet access
                if response.status_code == 204:
                    return True
                # If we get 200 OK, we might be behind a captive portal
                elif response.status_code == 200 and "generate_204" in url:
                    # Captive portal intercepts and returns 200
                    return False
        except httpx.RequestError as e:
            logger.debug(f"Connectivity check failed for {url}: {e}")
            pass
            
    return False
