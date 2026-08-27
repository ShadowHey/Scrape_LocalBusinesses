import time
import subprocess
import logging
from connectivity import check_internet
from config import TEST_URLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

def run_health_checker():
    logging.info("Starting simple internet health checker...")
    
    while True:
        # Check internet using the existing logic in connectivity.py
        is_connected = check_internet(TEST_URLS)
        
        if is_connected:
            logging.info("Internet is connected. Checking again in 10 seconds...")
            time.sleep(10)
        else:
            logging.warning("Internet disconnected! Running watchdog script to reconnect...")
            # Run the existing script to force a connection to the IIT BHU Wi-Fi using the exact same python executable
            import sys
            subprocess.run([sys.executable, "main.py", "--force-login"])
            
            logging.info("Reconnect attempt finished. Resuming health checks in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_health_checker()
